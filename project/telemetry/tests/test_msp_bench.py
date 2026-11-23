"""msp_bench.py: no drone needed.

1. Its decoders agree with inav_telemetry.py (the reference decoders) on every
   real reply in inav/msp/captures/, so the bench does not become a fourth
   decoder that silently disagrees ("Three decoders, one truth" in the README).
2. Its MSP v2 framing and parser.
3. Short end-to-end runs against msp_dashboard/tools/fake_fc.py: the bench CSV, the
   logbook run folder and history.csv (was measure_wifi_rtt.py), and --capture
   (was msp_inventory.py), whose recording must replay like the real ones.
4. The check that refuses a serial port another program already has open.
"""
import csv
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import inav_telemetry as t
import msp_bench as b
import pytest
from conftest import reply

HERE = Path(__file__).resolve().parents[1]
CAPTURES = HERE / "inav" / "msp" / "captures"
FAKE_FC = HERE / "msp_dashboard" / "tools" / "fake_fc.py"


def captured(cmd):
    """Payloads of every good reply to `cmd` in all recordings."""
    out = []
    for path in sorted(CAPTURES.glob("*.jsonl")):
        for line in path.read_text().splitlines()[1:]:
            r = json.loads(line)
            if r.get("cmd") == cmd and r.get("ok") and r.get("hex"):
                out.append(reply(r["hex"])[1])
    return out


def payloads(cmd):
    p = captured(cmd)
    if not p:
        pytest.skip(f"no recording of command {cmd}")
    return p


# ---------- 1. same values as the reference decoders ----------

def test_raw_imu_matches_reference():
    for p in payloads(b.MSP_RAW_IMU):
        mine, ref = b.dec_raw_imu(p), t.d_raw_imu(p)
        assert [mine["acc_x_g"], mine["acc_y_g"], mine["acc_z_g"]] == pytest.approx([a / 512 for a in ref["acc"]])
        assert [mine["gyro_x_dps"], mine["gyro_y_dps"], mine["gyro_z_dps"]] == list(ref["gyro"])


def test_attitude_matches_reference():
    for p in payloads(b.MSP_ATTITUDE):
        mine, ref = b.dec_attitude(p), t.d_attitude(p)
        assert mine["roll_deg"] == pytest.approx(ref["roll_deg"])
        assert mine["pitch_deg"] == pytest.approx(ref["pitch_deg"])
        assert mine["yaw_deg"] == ref["heading_deg"]


def test_altitude_matches_reference():
    for p in payloads(b.MSP_ALTITUDE):
        mine, ref = b.dec_altitude(p), t.d_altitude(p)
        assert mine["est_alt_cm"] / 100 == pytest.approx(ref["alt_m"])
        assert mine["est_vario_cms"] / 100 == pytest.approx(ref["vario_ms"])


def test_analog_matches_reference():
    for p in payloads(b.MSP2_INAV_ANALOG):
        mine, ref = b.dec_analog(p), t.d_inav_analog(p)
        assert mine["vbat_v"] == pytest.approx(ref["voltage_v"])
        assert mine["current_a"] == pytest.approx(ref["current_a"])
        assert mine["mah_drawn"] == ref["mah_drawn"]
        assert mine["battery_pct"] == ref["battery_pct"]


def test_status_and_arming_match_reference():
    for p in payloads(b.MSP2_INAV_STATUS):
        mine, ref = b.dec_status(p), t.d_inav_status(p)
        assert mine["cycle_time_us"] == ref["cycle_time_us"]
        assert mine["i2c_errors"] == ref["i2c_errors"]
        assert mine["cpu_load_pct"] == ref["cpu_load_pct"]
        flags = int.from_bytes(p[9:13], "little")
        assert [n.lower() for n in b.arming_blockers(flags)] == ref["arming_blockers"]


def test_rangefinder_matches_reference():
    for p in payloads(b.MSP_SONAR_ALTITUDE):
        mine, ref = b.dec_sonar(p), t.d_rangefinder(p)
        assert bool(mine["rangefinder_valid"]) == ref["valid"]
        if ref["valid"]:
            assert mine["rangefinder_cm"] / 100 == pytest.approx(ref["distance_m"])


def test_local_pose_matches_reference():
    for p in payloads(b.MSP2_INAV_FULL_LOCAL_POSE):
        mine, ref = b.dec_local_pose(p), t.d_local_pose(p)
        assert [mine["pose_x_cm"], mine["pose_y_cm"], mine["pose_z_cm"]] == \
            pytest.approx([v * 100 for v in ref["pos_m"]])


def test_rc_matches_reference():
    for p in payloads(b.MSP_RC):
        mine, ref = b.dec_rc(p), t.u16_list(p)
        assert [mine[f"rc_ch{i + 1}_us"] for i in range(len(mine))] == ref[:len(mine)]


# ---------- 2. framing ----------

def test_frame_round_trip_and_crc():
    frame = b.encode_v2(b.MSP_ATTITUDE, b"\x01\x02", b">")
    assert frame == t.build_frame(b.MSP_ATTITUDE, b"\x01\x02").replace(b"$X<", b"$X>", 1)
    parser = b.MspParser()
    frames = parser.feed(b"junk" + frame[:5])
    assert frames == []
    frames = parser.feed(frame[5:])
    assert [(f.cmd, f.payload, f.error) for f in frames] == [(b.MSP_ATTITUDE, b"\x01\x02", False)]
    assert parser.garbage_bytes == 4

    bad = bytearray(frame)
    bad[-1] ^= 0xFF
    assert b.MspParser().feed(bytes(bad)) == []


def test_error_reply_is_flagged():
    parser = b.MspParser()
    (f,) = parser.feed(b.encode_v2(0x2103, b"", b"!"))
    assert f.error


# ---------- 3. end to end against the fake FC ----------

def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


@pytest.fixture
def fake_fc():
    port = free_port()
    proc = subprocess.Popen([sys.executable, str(FAKE_FC), "--port", str(port), "--no-arm"],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        try:
            socket.create_connection(("127.0.0.1", port), timeout=0.2).close()
            break
        except OSError:
            time.sleep(0.05)
    yield port
    proc.terminate()
    proc.wait(timeout=5)


def test_bench_run_writes_csv(fake_fc, tmp_path):
    out = tmp_path / "bench.csv"
    raw = tmp_path / "raw.csv"
    run = subprocess.run(
        [sys.executable, str(HERE / "msp_bench.py"), "--tcp", f"127.0.0.1:{fake_fc}",
         "--duration", "1", "--rtt-count", "5", "--load-windows", "1,2", "--load-duration", "0.5",
         "--burst", "4", "--connect-wait", "2", "--color", "never",
         "--out", str(out), "--raw", str(raw)],
        capture_output=True, text=True, timeout=60)
    # fake_fc reports NOT_LEVEL while disarmed, so FAIL (1) is a correct result too
    assert run.returncode in (0, 1), run.stdout + run.stderr
    rows = list(csv.DictReader(out.open()))
    sections = {r["section"] for r in rows}
    assert {"info", "sensor_status", "sensors", "derived", "latency", "link"} <= sections
    assert all(r["status"] in ("PASS", "WARN", "FAIL", "INFO") for r in rows)
    info = {r["item"]: r["value"] for r in rows if r["section"] == "info"}
    assert info["fc_variant"] == "INAV"
    assert info["armed"] == "no"
    assert raw.exists() and raw.stat().st_size > 0
    assert "RESULT" in run.stdout


def test_logbook_run_keeps_the_wifi_rtt_columns(fake_fc, tmp_path, monkeypatch):
    sys.path.insert(0, str(b.SCRIPTS_DIR))
    import logbook
    monkeypatch.setattr(logbook, "LOGS", str(tmp_path))
    code = b.main(["--tcp", f"127.0.0.1:{fake_fc}", "--skip", "sensors,load", "--rtt-commands", "API_VERSION",
                   "--rtt-count", "20", "--connect-wait", "2", "--color", "never",
                   "--logbook", "pytest, fake FC", "--logbook-name", "wifi_rtt"])
    assert code in (0, 1)
    (run,) = (tmp_path / "measurements" / "wifi_rtt").glob("20*")
    assert {"meta.json", "bench.csv", "samples.csv", "values.json"} <= {p.name for p in run.iterdir()}
    meta = json.loads((run / "meta.json").read_text())
    assert meta["note"] == "pytest, fake FC" and meta["link"].startswith("tcp://")
    with open(tmp_path / "measurements" / "wifi_rtt" / "history.csv", newline="") as f:
        (row,) = list(csv.DictReader(f))
    # the columns measure_wifi_rtt.py wrote, so the old history stays comparable
    for key in ("host", "duration_s", "rate_hz", "sent", "answered", "lost", "lost_pct", "late",
                "corrupted", "min_ms", "median_ms", "p90_ms", "p99_ms", "max_ms", "jitter_ms", "note"):
        assert key in row, key
    assert row["sent"] == "20" and row["lost"] == "0" and row["note"] == "pytest, fake FC"


def test_capture_replays_like_the_real_recordings(fake_fc, tmp_path):
    code = b.main(["--tcp", f"127.0.0.1:{fake_fc}", "--capture", "bench_test", "--capture-count", "3",
                   "--capture-dir", str(tmp_path), "--no-copy", "--connect-wait", "2", "--color", "never",
                   "--out", str(tmp_path / "bench.csv")])
    assert code in (0, 1)
    lines = (tmp_path / "bench_test.jsonl").read_text().splitlines()
    header, records = json.loads(lines[0]), [json.loads(line) for line in lines[1:]]
    assert header["state"] == "bench_test" and header["setup"]["fc"] == "INAV 9.1.0"
    assert len(records) == 3 * len(b.CAPTURE_MSGS)
    assert [r["name"] for r in records[::3]] == [name for name, _ in b.CAPTURE_MSGS]
    good = [r for r in records if r.get("ok")]
    assert good, "no good replies recorded"
    for r in good:
        cmd, payload = reply(r["hex"])
        assert cmd == r["cmd"]
    att = [reply(r["hex"])[1] for r in good if r["name"] == "MSP_ATTITUDE"]
    assert att and all(-180 <= t.d_attitude(p)["roll_deg"] <= 180 for p in att)
    # fake_fc answers MSP2_INAV_GET_LINK_STATS with an error reply: kept as ok false
    assert all(r.get("ok") is False for r in records if r["name"] == "MSP2_INAV_GET_LINK_STATS")


def test_capture_refreshes_copies_with_the_same_name(tmp_path):
    src = tmp_path / "new.jsonl"
    src.write_text("new\n")
    ros = tmp_path / "project" / "ros2" / "src"
    (ros / "pkg" / "test" / "data").mkdir(parents=True)
    copy = ros / "pkg" / "test" / "data" / "new.jsonl"
    copy.write_text("old\n")
    rep = b.Report("x", "h", "l")
    assert b.refresh_capture_copies(rep, src, ros) == [copy]
    assert copy.read_text() == "new\n"


@pytest.mark.skipif(not os.path.isdir("/proc"), reason="reads /proc (Linux)")
def test_busy_serial_port_is_detected(tmp_path):
    port = tmp_path / "fake_tty"
    port.write_text("")
    holder = subprocess.Popen([sys.executable, "-c",
                               f"f = open({str(port)!r}); import time; time.sleep(30)"])
    try:
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline and not b.processes_using(str(port)):
            time.sleep(0.05)
        assert holder.pid in [pid for pid, _ in b.processes_using(str(port))]
    finally:
        holder.kill()
        holder.wait()
