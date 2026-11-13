"""Replay of real drone recordings through the MSP parser and decoders.

The recordings (telemetry/inav/captures/, from the INAV-4 branch, #125) hold
every raw MSP reply the drone sent in four bench states, about 20 per message:
OddityRC F7 on INAV 9.1.0, esp-link bridge, props off, receiver not bound.
The capture README says what the drone was doing in each one; these tests
check that the decoded values agree with it, for every frame, not just one.

Each line of a .jsonl file is one request:
    {"name": "MSP_ATTITUDE", "cmd": 108, "ok": true, "hex": "24583e006c..."}
ok false: the reply came back damaged (bad CRC or cut short).
"error": "timeout": no reply, no hex.
"""
import json
from pathlib import Path

import inav_telemetry as t
import pytest

CAPTURES = Path(__file__).resolve().parents[1] / "inav" / "captures" / "inav" / "msp" / "captures"
STATES = ["flat_still", "tilted", "radio_off", "flow_moving"]

# The main poller's decoders, by MSP command number.
DECODERS = {cmd: decode for cmd, decode in {**t.STATIC, **t.LIVE}.values()}


def load(state):
    """(header, requests) of one recording."""
    lines = (CAPTURES / f"{state}.jsonl").read_text().splitlines()
    return json.loads(lines[0]), [json.loads(line) for line in lines[1:]]


def good(state, name):
    """Payloads of every undamaged reply to `name` in a recording."""
    return [bytes.fromhex(r["hex"])[8:-1] for r in load(state)[1]
            if r["name"] == name and r.get("ok")]


def frames_in(data):
    c = t.MSPClient.__new__(t.MSPClient)
    c.buf = data
    found = []
    while (frame := c._next_frame()) is not None:
        found.append(frame)
    return found


@pytest.fixture
def modes(monkeypatch, request):
    """MODE_NAMES from the recording's own MSP_BOXNAMES, as at start-up."""
    names = t.d_box_names(good(request.param, "MSP_BOXNAMES")[0])
    monkeypatch.setattr(t, "MODE_NAMES", names)
    return names


# ---------- the recordings themselves ----------

@pytest.mark.parametrize("state", STATES)
def test_recording_header(state):
    header, requests = load(state)
    assert header["state"] == state
    assert header["setup"]["fc"] == "INAV 9.1.0"
    assert len([r for r in requests if r.get("ok")]) > 250


@pytest.mark.parametrize("state", STATES)
def test_timeouts_have_no_frame(state):
    for r in load(state)[1]:
        if "error" in r:
            assert r["error"] == "timeout" and "hex" not in r


# ---------- framing: every reply, through the real parser ----------

@pytest.mark.parametrize("state", STATES)
def test_every_good_reply_is_whole_with_a_valid_crc(state):
    for r in load(state)[1]:
        if not r.get("ok"):
            continue
        frame = bytes.fromhex(r["hex"])
        assert frame[:3] == b"$X>", r["name"]
        assert int.from_bytes(frame[4:6], "little") == r["cmd"], r["name"]
        assert len(frame) == 9 + int.from_bytes(frame[6:8], "little"), r["name"]
        assert t.crc8_dvb_s2(frame[3:-1]) == frame[-1], r["name"]


@pytest.mark.parametrize("state", STATES)
def test_parser_reads_every_good_reply(state):
    for r in load(state)[1]:
        if r.get("ok"):
            [(cmd, ok, payload)] = frames_in(bytes.fromhex(r["hex"]))
            assert (cmd, ok) == (r["cmd"], True), r["name"]
            assert payload == bytes.fromhex(r["hex"])[8:-1]


@pytest.mark.parametrize("state", STATES)
def test_parser_rejects_every_damaged_reply(state):
    for r in load(state)[1]:
        if r.get("ok") is False and "hex" in r:
            found = frames_in(bytes.fromhex(r["hex"]))
            assert r["cmd"] not in [cmd for cmd, ok, _ in found if ok], r["name"]


@pytest.mark.parametrize("state", STATES)
def test_every_good_reply_decodes_fully(state):
    # Real data must decode, not fall back to a raw payload in poll().
    for r in load(state)[1]:
        if r.get("ok") and r["cmd"] in DECODERS:
            DECODERS[r["cmd"]](bytes.fromhex(r["hex"])[8:-1])


# ---------- what the drone was doing: one test per state ----------

def test_flat_still_is_level():
    for a in [t.d_attitude(p) for p in good("flat_still", "MSP_ATTITUDE")]:
        assert -2.0 <= a["roll_deg"] <= 0.0
        assert -7.0 <= a["pitch_deg"] <= -5.0          # the books were not quite flat
        assert a["heading_deg"] in (48, 49)
    for imu in [t.d_raw_imu(p) for p in good("flat_still", "MSP_RAW_IMU")]:
        assert imu["acc"][2] > 450                     # gravity straight down Z
        assert abs(imu["acc"][1]) < 60


@pytest.mark.parametrize("modes", ["tilted"], indirect=True)
def test_tilted_rolls_about_46_degrees(modes):
    for a in [t.d_attitude(p) for p in good("tilted", "MSP_ATTITUDE")]:
        assert 44.0 <= a["roll_deg"] <= 48.0
    for imu in [t.d_raw_imu(p) for p in good("tilted", "MSP_RAW_IMU")]:
        _, y, z = imu["acc"]
        assert y > 300 and z > 300 and abs(y - z) < 40  # gravity split evenly: about 45 deg
    for s in [t.d_inav_status(p) for p in good("tilted", "MSP2_INAV_STATUS")]:
        assert "not_level" in s["arming_blockers"]


@pytest.mark.parametrize("modes", ["radio_off"], indirect=True)
def test_radio_off_is_failsafe(modes):
    statuses = [t.d_inav_status(p) for p in good("radio_off", "MSP2_INAV_STATUS")]
    assert statuses
    for s in statuses:
        assert s["flight_modes"] == ["FAILSAFE"]
        assert "rc_link" in s["arming_blockers"]
        assert s["armed"] is False
    for rc in [t.u16_list(p) for p in good("radio_off", "MSP_RC")]:
        assert rc[3] == 885                            # throttle channel at its failsafe value


def test_flow_moving_sees_motion():
    flows = [t.d_opflow(p) for p in good("flow_moving", "MSP2_INAV_OPTICAL_FLOW")]
    fastest = max(max(abs(f["flow_rate_x_dps"]), abs(f["flow_rate_y_dps"])) for f in flows)
    assert fastest >= 40                               # about 56 deg/s while sliding
    qualities = [f["quality"] for f in flows]
    assert 0 in qualities                              # lost the surface for a moment
    assert sum(q == 100 for q in qualities) > len(qualities) / 2


@pytest.mark.parametrize("state", ["flat_still", "tilted", "radio_off"])
def test_still_states_have_little_flow(state):
    flows = [t.d_opflow(p) for p in good(state, "MSP2_INAV_OPTICAL_FLOW")]
    assert max(max(abs(f["flow_rate_x_dps"]), abs(f["flow_rate_y_dps"])) for f in flows) < 25


# ---------- the same in every state ----------

@pytest.mark.parametrize("state", STATES)
def test_identity(state):
    assert {t.d_text(p) for p in good(state, "MSP_FC_VARIANT")} == {"INAV"}
    assert {t.d_fc_version(p) for p in good(state, "MSP_FC_VERSION")} == {"9.1.0"}
    assert {t.d_api_version(p)["api"] for p in good(state, "MSP_API_VERSION")} == {"2.5"}


@pytest.mark.parametrize("state", STATES)
def test_mode_names(state):
    for p in good(state, "MSP_BOXNAMES"):
        names = t.d_box_names(p)
        assert names[0] == "ARM" and names[17] == "FAILSAFE"


@pytest.mark.parametrize("modes", STATES, indirect=True)
def test_disarmed_on_the_bench_without_a_rangefinder(modes, request):
    state = request.node.callspec.params["modes"]
    for s in [t.d_inav_status(p) for p in good(state, "MSP2_INAV_STATUS")]:
        assert s["armed"] is False and s["was_ever_armed"] is False
        assert s["sensors"] == ["acc", "baro", "opflow", "temp"]   # no rangefinder fitted
        assert s["hardware_ok"] is True
    for m in [t.u16_list(p) for p in good(state, "MSP_MOTOR")]:
        assert m[:4] == [1000] * 4                                  # 4 motors stopped


@pytest.mark.parametrize("state", STATES)
def test_battery(state):
    for b in [t.d_inav_analog(p) for p in good(state, "MSP2_INAV_ANALOG")]:
        assert 16.0 <= b["voltage_v"] <= 16.4                       # 4S, charged
        assert b["cell_count"] == 4
        assert b["battery_state"] == "ok"
