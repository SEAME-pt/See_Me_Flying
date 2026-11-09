"""MSP v2 framing in inav_telemetry.py: checksum, request frames, reply parser.

No drone and no network: the reply parser is fed bytes directly, and
MSPClient.request() talks to a fake socket. Real frames come from the INAV-4
captures (OddityRC F7, INAV 9.1.0, esp-link bridge, 2026-11-09).

MSP v2 frame:  '$' 'X' dir | flag | cmd (u16 LE) | size (u16 LE) | payload | crc
               dir: '<' request, '>' reply, '!' error reply
               crc: CRC-8/DVB-S2 over flag, cmd, size and payload
"""
import socket
import struct
import time

import pytest

from inav_telemetry import build_frame, crc8_dvb_s2, MSPClient

# Real replies from the drone (flat_still.jsonl unless noted).
API_VERSION = "24583e0001000300000205a6"
FC_VARIANT = "24583e0002000400494e415694"
ATTITUDE = "24583e006c000600f7ffc0ff300089"
INAV_STATUS = "24583e0000201600ff013200a3000d00000002041000000200000000000007"
INAV_ANALOG = "24583e00022018004050063e00e90300000c000000cf0000000000000052000072"
OPFLOW_MOVING = "24583e00012009005c2e00090000000000c3"         # flow_moving.jsonl
REAL_FRAMES = [API_VERSION, FC_VARIANT, ATTITUDE, INAV_STATUS, INAV_ANALOG, OPFLOW_MOVING]

# radio_off.jsonl: a long MSP_BOXNAMES reply cut short on the link, with a complete,
# valid MSP_ALTITUDE reply inside it (from byte 80). Recorded with ok: false.
CORRUPT_BOXNAMES = (
    "24583e007400670141524d3b50524541524d3b4d554c54492046554e4354494f4e3b414e474c453b"
    "484f52495a4f4e3b5455524e204153534953543b48454144494e4720484f4c443b43414d53544142"
)
ALTITUDE_INSIDE = "24583e006d000a0000000000000010000000fc"


def client(chunks=(), timeout=0.2):
    """An MSPClient without a real connection; its socket hands out `chunks`."""
    c = MSPClient.__new__(MSPClient)
    c.sock = FakeSocket(chunks)
    c.timeout = timeout
    c.buf = b""
    return c


class FakeSocket:
    """recv() returns the next chunk, then times out like the real 50 ms socket."""

    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.sent = []

    def sendall(self, data):
        self.sent.append(data)

    def recv(self, _size):
        if not self.chunks:
            time.sleep(0.005)
            raise socket.timeout
        return self.chunks.pop(0)


def frames_in(data):
    """Every (cmd, ok, payload) the parser finds in `data`, in order."""
    c = client()
    c.buf = data
    found = []
    while (frame := c._next_frame()) is not None:
        found.append(frame)
    return found


# ---------- checksum ----------

def test_crc_standard_check_value():
    # Published check value of CRC-8/DVB-S2: independent of this code.
    assert crc8_dvb_s2(b"123456789") == 0xBC


def test_crc_of_nothing_is_zero():
    assert crc8_dvb_s2(b"") == 0


@pytest.mark.parametrize("hex_frame", REAL_FRAMES)
def test_crc_matches_real_drone_frames(hex_frame):
    frame = bytes.fromhex(hex_frame)
    assert crc8_dvb_s2(frame[3:-1]) == frame[-1]


def test_crc_detects_a_single_flipped_bit():
    body = bytes.fromhex(ATTITUDE)[3:-1]
    good = crc8_dvb_s2(body)
    for i in range(len(body)):
        for bit in range(8):
            flipped = bytearray(body)
            flipped[i] ^= 1 << bit
            assert crc8_dvb_s2(bytes(flipped)) != good, f"byte {i} bit {bit}"


# ---------- request frames ----------

def test_request_frame_layout():
    frame = build_frame(108)                     # MSP_ATTITUDE, no payload
    assert frame[:3] == b"$X<"
    flag, cmd, size = struct.unpack_from("<BHH", frame, 3)
    assert (flag, cmd, size) == (0, 108, 0)
    assert len(frame) == 9
    assert frame[-1] == crc8_dvb_s2(frame[3:-1])


def test_request_frame_with_payload():
    frame = build_frame(0x2001, b"\x01\x02\x03")
    assert struct.unpack_from("<H", frame, 6)[0] == 3
    assert frame[8:11] == b"\x01\x02\x03"
    assert frame[-1] == crc8_dvb_s2(frame[3:-1])


@pytest.mark.parametrize("cmd, low, high", [(1, 0x01, 0x00), (0x2000, 0x00, 0x20),
                                            (0x2001, 0x01, 0x20), (0x2220, 0x20, 0x22)])
def test_v2_command_ids_are_two_bytes_little_endian(cmd, low, high):
    frame = build_frame(cmd)
    assert (frame[4], frame[5]) == (low, high)


def test_request_matches_the_reply_header():
    # Same flag/cmd/size layout as the drone's reply, only the direction differs.
    reply_header = bytes.fromhex(API_VERSION)[3:6]
    assert build_frame(1)[3:6] == reply_header


# ---------- reply parser ----------

def test_parses_a_real_reply():
    [(cmd, ok, payload)] = frames_in(bytes.fromhex(ATTITUDE))
    assert (cmd, ok) == (108, True)
    assert payload == bytes.fromhex("f7ffc0ff3000")


def test_back_to_back_replies_come_out_in_order():
    data = b"".join(bytes.fromhex(h) for h in REAL_FRAMES)
    assert [f[0] for f in frames_in(data)] == [1, 2, 108, 0x2000, 0x2002, 0x2001]


def test_garbage_before_a_frame_is_skipped():
    data = b"\x00\xff$$X?noise" + bytes.fromhex(ATTITUDE)
    assert [f[0] for f in frames_in(data)] == [108]


def test_bad_crc_is_dropped_and_the_next_frame_still_parses():
    bad = bytearray.fromhex(ATTITUDE)
    bad[9] ^= 0x01                               # one payload bit
    data = bytes(bad) + bytes.fromhex(FC_VARIANT)
    assert [f[0] for f in frames_in(data)] == [2]


def test_error_reply_is_reported_not_ok():
    frame = b"$X!" + bytes.fromhex(ATTITUDE)[3:]  # same frame, error direction
    [(cmd, ok, _)] = frames_in(frame)
    assert (cmd, ok) == (108, False)


def test_own_request_echoed_back_is_ignored():
    data = build_frame(108) + bytes.fromhex(FC_VARIANT)
    assert [f[0] for f in frames_in(data)] == [2]


def test_impossible_size_is_skipped():
    header = b"$X>" + struct.pack("<BHH", 0, 108, 5000)      # over the 4096 limit
    data = header + bytes.fromhex(ATTITUDE)
    assert [f[0] for f in frames_in(data)] == [108]


def test_incomplete_frame_waits_for_the_rest():
    frame = bytes.fromhex(ATTITUDE)
    c = client()
    c.buf = frame[:10]
    assert c._next_frame() is None
    c.buf += frame[10:]
    assert c._next_frame()[0] == 108


def test_marker_split_across_two_reads():
    frame = bytes.fromhex(ATTITUDE)
    c = client()
    c.buf = b"noise" + frame[:1]                 # ends with '$'
    assert c._next_frame() is None
    c.buf += frame[1:]
    assert c._next_frame()[0] == 108


@pytest.mark.xfail(strict=True, reason=(
    "Known weakness: on a bad CRC the parser drops the whole length the corrupt "
    "header claimed (368 bytes here), swallowing valid replies inside it. It should "
    "drop only the '$X' and search again. Seen on the drone: INAV-4 retries "
    "MSP_BOXNAMES because of it. Fix _next_frame, then remove this xfail."))
def test_valid_reply_inside_a_corrupt_one_is_recovered():
    data = bytes.fromhex(CORRUPT_BOXNAMES + ALTITUDE_INSIDE + ATTITUDE)
    data += bytes(400)                           # later traffic, so the bad frame looks whole
    assert [f[0] for f in frames_in(data)][:2] == [109, 108]


# ---------- request(): send, wait, match ----------

def test_request_sends_the_frame_and_returns_the_payload():
    c = client([bytes.fromhex(ATTITUDE)])
    assert c.request(108) == (True, bytes.fromhex("f7ffc0ff3000"))
    assert c.sock.sent == [build_frame(108)]


def test_reply_split_over_several_reads():
    frame = bytes.fromhex(ATTITUDE)
    c = client([frame[:4], frame[4:9], frame[9:]])
    assert c.request(108)[0] is True


def test_stale_reply_to_another_command_is_skipped():
    # A late reply to an earlier, timed-out request arrives first.
    c = client([bytes.fromhex(FC_VARIANT), bytes.fromhex(ATTITUDE)])
    ok, payload = c.request(108)
    assert ok is True and len(payload) == 6


def test_error_reply_returns_not_ok():
    c = client([b"$X!" + bytes.fromhex(ATTITUDE)[3:]])
    assert c.request(108)[0] is False


def test_no_reply_times_out():
    c = client([], timeout=0.2)
    start = time.monotonic()
    assert c.request(108) == (None, None)
    assert 0.2 <= time.monotonic() - start < 0.5


def test_closed_connection_raises():
    c = client([b""])
    with pytest.raises(ConnectionError):
        c.request(108)
