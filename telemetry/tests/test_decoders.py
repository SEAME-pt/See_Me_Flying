"""Payload decoders in inav_telemetry.py: units, scaling, bit fields.

Three kinds of tests:
- hand-made payloads (struct.pack) with chosen values, to pin the units;
- real payloads from the INAV-4 captures (INAV 9.1.0), checked against what
  the drone was doing (telemetry/inav/captures/README.md on that branch);
- fixed bugs, at the end: where fc_bridge's C++ decoders, written from the
  INAV source, disagreed with this script. They keep the bugs from coming back.
"""
import struct

from conftest import reply
import inav_telemetry as t
import pytest

BOXNAMES = (
    "24583e007400670141524d3b50524541524d3b4d554c54492046554e4354494f4e3b414e474c453b484f"
    "52495a4f4e3b5455524e204153534953543b48454144494e4720484f4c443b43414d535441423b484541"
    "44465245453b4845414441444a3b46505620414e474c45204d49583b4d43204252414b494e473b4e4156"
    "20414c54484f4c443b4245455045523b424545504552204d5554453b4f5344204f46463b424c41434b42"
    "4f583b4641494c534146453b43414d45524120434f4e54524f4c20313b43414d45524120434f4e54524f"
    "4c20323b43414d45524120434f4e54524f4c20333b4f534420414c5420313b4f534420414c5420323b4f"
    "534420414c5420333b4d5350205243204f564552524944453b545552544c453b4d495845522050524f46"
    "494c4520323b4d49584552205452414e534954494f4e3b47494d42414c204c4556454c2054494c543b47"
    "494d42414c204c4556454c20524f4c4c3b47494d42414c2043454e5445523b29"
)


@pytest.fixture
def drone_modes(monkeypatch):
    """MODE_NAMES as filled at start-up from the drone's MSP_BOXNAMES reply."""
    names = t.d_box_names(reply(BOXNAMES)[1])
    monkeypatch.setattr(t, "MODE_NAMES", names)
    return names


# ---------- hand-made payloads: units and scaling ----------

def test_attitude_tenths_of_a_degree():
    d = t.d_attitude(struct.pack("<hhh", 455, -123, 270))
    assert d == {"roll_deg": 45.5, "pitch_deg": -12.3, "heading_deg": 270}


def test_altitude_cm_to_m():
    d = t.d_altitude(struct.pack("<ih", 1234, -56))
    assert d == {"alt_m": 12.34, "vario_ms": -0.56}


def test_raw_imu_axis_order():
    d = t.d_raw_imu(struct.pack("<9h", 1, 2, 3, 4, 5, 6, 7, 8, 9))
    assert d == {"acc": (1, 2, 3), "gyro": (4, 5, 6), "mag": (7, 8, 9)}


def test_opflow_signed_rates():
    d = t.d_opflow(struct.pack("<Bhhhh", 200, -37, 9, 3, -4))
    assert d == {"quality": 200, "flow_rate_x_dps": -37, "flow_rate_y_dps": 9,
                 "body_rate_x_dps": 3, "body_rate_y_dps": -4}


def test_msp_analog_scaling():
    d = t.d_analog(struct.pack("<BHHh", 162, 1500, 1023, 1234))
    assert d == {"vbat_v": 16.2, "mah_drawn": 1500, "rssi_pct": 100.0, "current_a": 12.34}


def test_inav_analog_scaling_and_flags():
    flags = 4 << 4 | 2 << 2 | 0b10            # 4 cells, critical, capacity thresholds
    p = struct.pack("<BHhIIIIBH", flags, 1480, -150, 2220, 900, 13000, 1200, 35, 512)
    d = t.d_inav_analog(p)
    assert d["voltage_v"] == 14.8
    assert d["current_a"] == -1.5
    assert d["power_w"] == 22.2
    assert (d["mah_drawn"], d["mwh_drawn"], d["remaining_capacity"]) == (900, 13000, 1200)
    assert d["battery_pct"] == 35
    assert d["cell_count"] == 4
    assert d["battery_state"] == "critical"
    assert d["uses_capacity_thresholds"] is True
    assert d["full_when_plugged_in"] is False
    assert d["rssi_pct"] == 50.0


@pytest.mark.parametrize("state, name", enumerate(t.BATTERY_STATES))
def test_every_battery_state(state, name):
    p = struct.pack("<BHhIIIIBH", state << 2, 0, 0, 0, 0, 0, 0, 0, 0)
    assert t.d_inav_analog(p)["battery_state"] == name


def test_rangefinder_cm_to_m():
    assert t.d_rangefinder(struct.pack("<i", 123)) == {"valid": True, "distance_m": 1.23}


def test_rangefinder_minus_one_is_out_of_range():
    assert t.d_rangefinder(struct.pack("<i", -1)) == {"valid": False, "code": -1}


def test_raw_gps_degrees_and_optional_hdop():
    p = struct.pack("<BBiihHH", 2, 9, 387223456, -91393210, 120, 250, 1805)
    d = t.d_raw_gps(p)
    assert d["lat"] == pytest.approx(38.7223456)
    assert d["lon"] == pytest.approx(-9.139321)
    assert (d["fix"], d["sats"], d["alt_m"]) == (2, 9, 120)
    assert d["speed_ms"] == 2.5 and d["course_deg"] == 180.5
    assert "hdop" not in d
    assert t.d_raw_gps(p + struct.pack("<H", 150))["hdop"] == 1.5


def test_comp_gps():
    assert t.d_comp_gps(struct.pack("<HhB", 42, -90, 0)) == {
        "home_dist_m": 42, "home_dir_deg": -90}


def test_u16_list_ignores_a_trailing_odd_byte():
    assert t.u16_list(struct.pack("<3H", 1000, 1500, 2000) + b"\x07") == [1000, 1500, 2000]


def test_text_strips_padding():
    assert t.d_text(b"INAV\x00\x00") == "INAV"


def test_box_names_split():
    assert t.d_box_names(b"ARM;ANGLE;FAILSAFE;") == ["ARM", "ANGLE", "FAILSAFE"]


# ---------- bit fields ----------

def test_sensor_bits():
    d = t.sensor_fields(0xA3)
    assert d == {"sensors": ["acc", "baro", "opflow", "temp"], "hardware_ok": True}
    assert t.sensor_fields(1 << 4)["sensors"] == ["rangefinder"]
    assert t.sensor_fields(1 << 15)["hardware_ok"] is False


def test_armed_bit_is_not_a_blocker():
    d = t.arming_fields(1 << 2 | 1 << 3)
    assert d == {"armed": True, "was_ever_armed": True, "arming_blockers": []}


def test_arming_blockers_named_in_bit_order():
    d = t.arming_fields(1 << 8 | 1 << 18 | 1 << 28)
    assert d["armed"] is False
    assert d["arming_blockers"] == ["not_level", "rc_link", "no_prearm"]


def test_flight_modes_from_names(monkeypatch):
    monkeypatch.setattr(t, "MODE_NAMES", ["ARM", "ANGLE", "HORIZON"])
    assert t.flight_modes(bytes([0b101, 0, 0, 0])) == ["ARM", "HORIZON"]


def test_flight_mode_without_a_name(monkeypatch):
    monkeypatch.setattr(t, "MODE_NAMES", ["ARM"])
    assert t.flight_modes(bytes([0, 1, 0, 0])) == ["mode_bit_8"]


# ---------- status messages ----------

def test_inav_status_fields(monkeypatch):
    monkeypatch.setattr(t, "MODE_NAMES", ["ARM", "ANGLE"])
    p = struct.pack("<HHHHBI", 500, 3, 0xA3, 27, 0x21, 1 << 2) + bytes([2, 0, 0, 0, 1])
    d = t.d_inav_status(p)
    assert (d["cycle_time_us"], d["i2c_errors"], d["cpu_load_pct"]) == (500, 3, 27)
    assert (d["pid_profile"], d["battery_profile"]) == (2, 3)
    assert d["armed"] is True
    assert d["flight_modes"] == ["ANGLE"]
    assert d["mixer_profile"] == 2


def test_inav_status_without_mixer_profile():
    p = struct.pack("<HHHHBI", 500, 0, 0, 0, 0, 0) + bytes(4)
    assert "mixer_profile" not in t.d_inav_status(p)


def test_status_and_status_ex(monkeypatch):
    monkeypatch.setattr(t, "MODE_NAMES", ["ARM"])
    base = struct.pack("<HHH", 1000, 0, 0x01) + bytes([1, 0, 0, 0]) + bytes([1])
    d = t.d_status(base)
    assert (d["cycle_time_us"], d["flight_modes"], d["profile"]) == (1000, ["ARM"], 2)
    ex = t.d_status_ex(base + struct.pack("<HH", 15, 1 << 8))
    assert ex["cpu_load_pct"] == 15 and ex["arming_blockers"] == ["not_level"]


# ---------- real payloads from the drone ----------

def test_identity():
    assert t.d_api_version(reply("24583e0001000300000205a6")[1]) == {
        "protocol": 0, "api": "2.5"}
    assert t.d_text(reply("24583e0002000400494e415694")[1]) == "INAV"
    assert t.d_fc_version(reply("24583e000300030009010008")[1]) == "9.1.0"
    assert t.d_text(reply("24583e000a000d0050494c4f5449582d42524f4f4ba5")[1]) == "PILOTIX-BROOK"


def test_drone_mode_names(drone_modes):
    assert len(drone_modes) == 31
    assert drone_modes[:2] == ["ARM", "PREARM"]
    assert drone_modes[17] == "FAILSAFE"         # bit 17, as the README notes


@pytest.mark.parametrize("hex_frame, roll, pitch, heading", [
    ("24583e006c000600f7ffc0ff300089", -0.9, -6.4, 48),     # flat_still
    ("24583e006c000600d20188ff650184", 46.6, -12.0, 357),   # tilted
    ("24583e006c000600ddffbfff01001d", -3.5, -6.5, 1),      # radio_off
])
def test_real_attitude(hex_frame, roll, pitch, heading):
    assert t.d_attitude(reply(hex_frame)[1]) == {
        "roll_deg": roll, "pitch_deg": pitch, "heading_deg": heading}


def test_real_imu_agrees_with_the_tilt():
    flat = t.d_raw_imu(reply("24583e00660012003400f6fffb01ffff0300000000000000000019")[1])
    tilted = t.d_raw_imu(reply("24583e006600120060006e016201000001000100000000000000b1")[1])
    assert flat["acc"] == (52, -10, 507)        # gravity on Z: level
    assert tilted["acc"][1:] == (366, 354)       # gravity split Y/Z: about 46 deg of roll
    assert flat["mag"] == (0, 0, 0)              # no compass fitted


def test_real_status_flat(drone_modes):
    d = t.d_inav_status(reply(
        "24583e0000201600ff013200a3000d00000002041000000200000000000007")[1])
    assert d["sensors"] == ["acc", "baro", "opflow", "temp"]
    assert "rangefinder" not in d["sensors"]
    assert d["armed"] is False
    assert d["arming_blockers"] == ["sensors_calibrating", "rc_link", "no_prearm"]
    assert d["flight_modes"] == ["FAILSAFE"]


def test_real_status_tilted_is_not_level(drone_modes):
    d = t.d_inav_status(reply(
        "24583e0000201600f8013200a3000e00000003041000000200000000000057")[1])
    assert "not_level" in d["arming_blockers"]


def test_real_battery():
    d = t.d_inav_analog(reply(
        "24583e00022018004050063e00e90300000c000000cf0000000000000052000072")[1])
    assert d["voltage_v"] == 16.16
    assert d["cell_count"] == 4
    assert d["battery_state"] == "ok"
    assert d["battery_pct"] == 82


def test_real_optical_flow_while_moving():
    d = t.d_opflow(reply("24583e00012009005c2e00090000000000c3")[1])
    assert d == {"quality": 92, "flow_rate_x_dps": 46, "flow_rate_y_dps": 9,
                 "body_rate_x_dps": 0, "body_rate_y_dps": 0}


# ---------- fixed bugs: where this script disagreed with fc_bridge ----------
# drone_fc_bridge/src/inav_decode.cpp (ROS-6 step A) was written from the INAV
# 9.1.0 source, and its comments named three places where this script was wrong.
# Each test says what INAV sends, so the bugs can't come back.

# The reasons arming is blocked: bits 6-16 and 18-30 of armingFlag_e
# (ARMING_DISABLED_ALL_FLAGS), the same as ARMING_BLOCKERS in inav_decode.hpp.
# Written out here rather than imported, so the test checks the script.
INAV_BLOCKER_BITS = [*range(6, 17), *range(18, 31)]


def test_only_real_arming_blockers_are_listed():
    # Was: every set bit except armed and was_ever_armed counted as a blocker, so the
    # simulator modes (bits 4, 5: set on INAV SITL) and unused bits (0, 1, 17, 31) were
    # reported as reasons arming is blocked.
    # INAV SITL, tilted: the only reason it can't arm is not_level.
    assert t.arming_fields(1 << 5 | 1 << 8)["arming_blockers"] == ["not_level"]
    every_bit = t.arming_fields(0xFFFFFFFF)["arming_blockers"]
    assert every_bit == [t.ARMING_BITS[i] for i in INAV_BLOCKER_BITS]


def test_rangefinder_zero_is_not_a_distance():
    # Was: reported as a valid 0.0 m. INAV sends 0 cm when no rangefinder is running
    # (its MSP rangefinder driver turns a real 0 into -1); fc_bridge calls it NO_READING.
    # The reply in every capture: no rangefinder fitted on the bench.
    cmd, payload = reply("24583e003a0004000000000079")
    assert cmd == 58
    assert t.d_rangefinder(payload)["valid"] is False


def test_inav_analog_negative_power_and_drawn():
    # Was: power, mAh drawn and mWh drawn, int32 in INAV, were read as uint32, so a
    # negative current gave a power of about 42949 kW.
    # The payload of AnalogHandBuilt in drone_fc_bridge/test/test_inav_decode.cpp.
    p = struct.pack("<BHhiiiIBH", 0x3B, 1110, -150, -1665, -7, -80, 0xF0000001, 17, 1023)
    d = t.d_inav_analog(p)
    assert d["current_a"] == -1.5
    assert d["power_w"] == -16.65
    assert (d["mah_drawn"], d["mwh_drawn"]) == (-7, -80)
    assert d["remaining_capacity"] == 0xF0000001


def test_real_rc_and_motors():
    rc = t.u16_list(reply(
        "24583e0069002200dc05dc05dc0575038b06dc05dc05dc05dc05dc05dc05dc05dc05dc05dc05dc05dc0581"
    )[1])
    assert len(rc) == 17 and rc[3] == 885         # throttle low
    motors = t.u16_list(reply("24583e0068001000e803e803e803e803000000000000000027")[1])
    assert motors[:4] == [1000] * 4               # 4 motors stopped, disarmed


# ---------- robustness: what poll() relies on ----------

@pytest.mark.parametrize("name", list(t.LIVE) + list(t.STATIC))
def test_short_or_odd_payload_only_raises_what_poll_catches(name):
    # poll() turns struct.error and IndexError into a raw payload; anything
    # else would crash the telemetry loop.
    _, decode = {**t.STATIC, **t.LIVE}[name]
    for n in range(40):
        for payload in (bytes(n), bytes([0xFF]) * n, bytes(range(n))):
            try:
                decode(payload)
            except (struct.error, IndexError):
                pass


def test_command_numbers():
    # The MSP command each entry asks for (INAV 9.1.0 msp_protocol*.h).
    cmds = {name: cmd for name, (cmd, _) in {**t.STATIC, **t.LIVE}.items()}
    assert cmds == {**cmds, "api_version": 1, "fc_variant": 2, "fc_version": 3,
                    "board_info": 4, "craft_name": 10, "mode_names": 116,
                    "attitude": 108, "altitude": 109, "imu_raw": 102,
                    "rc_channels": 105, "motors": 104, "inav_status": 0x2000,
                    "inav_analog": 0x2002, "opflow": 0x2001}


def test_raw_payload_is_hex_in_json_and_decimal_on_screen():
    raw = t.Raw(b"\x01\xff")
    assert t.to_json({"x": raw}) == '{"x": "01ff"}'
    assert t.fmt_value(raw) == "1 255"
    assert t.fmt_value(None) == "no reply"
