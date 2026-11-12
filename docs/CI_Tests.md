# CI tests: what exists and what to add

State of `main` on 2026-11-09 (commit `87c48fc`).

- [Part 1: tests that exist](#part-1-tests-that-exist)
- [Part 2: tests to add](#part-2-tests-to-add)
- [Order of work](#order-of-work)

---

# Part 1: tests that exist

There are 110 behaviour tests in 8 files, plus lint checks. All run in CI job `ros2-build-test` through `colcon test`. Paths are relative to `seame-docker/ros2_ws/src/`.

## 1.1 `drone_fc_bridge/test/test_failsafes.py` (9 tests, João Barros)

Starts the real `fc_bridge` node with default parameters (timeout 0.3 s, max_speed_xy 0.5, max_speed_z 0.3, max_yaw_rate 1.0). The test sends setpoints on `fc/setpoint_velocity` and reads what reaches Gazebo on `/X3/gazebo/command/twist`.

| Test | What it checks |
| --- | --- |
| `test_zero_without_setpoints` | With no setpoint, fc_bridge still publishes on every tick (≥10 in 1 s), and every command is zero |
| `test_fresh_setpoint_is_forwarded` | A setpoint within limits reaches Gazebo unchanged: vx 0.2, vy −0.1, vz 0.1, yaw 0.5 |
| `test_timeout_sends_zero` | After the setpoints stop, the last one is still followed until 0.3 s. After 0.3 s, only zeros go out |
| `test_nan_is_rejected_and_times_out` | NaN setpoints never reach Gazebo (every output is finite), and they don't keep the last good setpoint alive, so it times out to zero |
| `test_inf_is_rejected` | An infinite yaw rate is rejected and the output stays zero |
| `test_horizontal_clamp_keeps_direction` | (3, 4) m/s is cut to (0.3, 0.4): total speed 0.5, same direction |
| `test_vertical_and_yaw_clamp` | Vertical speed is limited to ±0.3 m/s and yaw rate to ±1.0 rad/s, in both directions |
| `test_roll_and_pitch_rates_are_zeroed` | Roll and pitch rates in the setpoint are forced to 0; the rest still passes |
| `test_sim_enable_is_published` | `/X3/enable` is published and is true (the sim drone is enabled) |

## 1.2 `drone_fc_bridge/test/test_state.py` (7 tests, João Barros)

Starts `fc_bridge` with all noise set to 0. The test plays Gazebo: it publishes `/X3/odom` at 50 Hz and reads `fc/odom`, `fc/attitude` and `fc/range`.

| Test | What it checks |
| --- | --- |
| `test_velocity_passes_through` | The sim velocity appears unchanged in `fc/odom` |
| `test_position_is_integrated_not_copied` | The sim says x = y = 5, but `fc/odom` ignores that and builds position from velocity × time, as optical flow would |
| `test_body_velocity_rotated_by_heading` | Facing +y (yaw 90°), moving forward increases world y, not x |
| `test_height_and_orientation_from_sim` | Height and orientation are copied from the sim into `fc/odom` and `fc/attitude` |
| `test_range_level` | Level at 1.2 m, the rangefinder reads 1.2 m and reports min 0.04 m and max 4.0 m |
| `test_range_reads_longer_when_tilted` | At 1 m height with 60° roll, the range reads 2.0 m (1 / cos 60°) |
| `test_range_out_of_range_is_inf` | Above the maximum it reads +inf, below the minimum −inf, and upside down +inf |

> Note: these tests use fc_bridge's **default** rangefinder (0.04–4.0 m, 27° cone, a VL53L1X-like sensor). The simulation itself loads `sim.yaml`, which configures the MTF-02P (0.02–6.0 m, 4° cone). So the sensor that actually flies in the sim isn't tested. See test C2 in Part 2.

## 1.3 `drone_fc_bridge/test/test_services.py` (4 tests, João Barros)

Starts `fc_bridge` and calls its `fc/arm` and `fc/hold` services.

| Test | What it checks |
| --- | --- |
| `test_starts_armed` | In the sim it starts armed, `/X3/enable` is true and `fc/status` reports backend `sim` |
| `test_disarm_and_rearm` | Disarming makes `/X3/enable` false and status disarmed; arming again restores both |
| `test_hold_sends_zero_despite_setpoints` | With hold on, the output is zero even though setpoints keep arriving, and status shows holding. With hold off, setpoints are followed again |
| `test_status_reports_setpoint_age` | After the setpoints stop, `fc/status.setpoint_age_s` grows past 0.5 s and `following_setpoints` becomes false |

## 1.4 `drone_fc_bridge/test/test_inav.py` (3 tests, João Barros)

Starts `fc_bridge` with `backend:=inav`, which is currently a stub for the real drone.

| Test | What it checks |
| --- | --- |
| `test_status_says_inav_and_disarmed` | Status says backend `inav` and disarmed. "Armed at start" must never apply to the real drone |
| `test_arm_is_refused` | `fc/arm` refuses both arm and disarm and answers that arming is done on the radio |
| `test_nothing_reaches_the_sim` | There are no publishers on the Gazebo topics: in INAV mode nothing is sent to the simulator |

## 1.5 `drone_mission/test/test_logic.py` (43 tests, João Barros)

Tests the mission state machine (`logic.py`) **without ROS**, against a toy drone: height follows the commanded vertical speed, the rangefinder reads 0.04–4.0 m, and there is optional sag and a ceiling. A whole flight runs in milliseconds.

**Takeoff**

| Test | What it checks |
| --- | --- |
| `test_starts_grounded_and_silent` | Starts GROUNDED and publishes nothing |
| `test_takeoff_hold_land` | A full flight: takeoff to 1.2 m (±5 cm), hold converges to ±1 cm and keeps publishing, land reaches the ground and goes silent. States go TAKEOFF → HOLD → LAND → GROUNDED |
| `test_takeoff_to_a_given_height` | Takeoff to a requested 0.8 m arrives within 5 cm |
| `test_takeoff_refused_without_range` | Takeoff is refused when there's no rangefinder |
| `test_takeoff_refused_above_range_max` | A 5 m target, beyond the sensor's range, is refused |
| `test_takeoff_refused_in_the_air` | A second takeoff while flying is refused |
| `test_takeoff_timeout_lands` | If the target can't be reached (ceiling at 0.6 m), the takeoff aborts and the drone lands |
| `test_cancel_takeoff_holds_where_it_is` | Cancelling a takeoff holds at the current height |
| `test_takeoff_refused_until_range_is_steady` | The range must read steadily for 1 s before takeoff is allowed |
| `test_range_gap_restarts_the_steady_time` | A gap in range readings restarts that 1 s wait |

**Goto**

| Test | What it checks |
| --- | --- |
| `test_goto_forward` | A 1 m forward move arrives within 10 cm and holds height within 3 cm |
| `test_goto_is_relative_to_heading` | After turning 90°, "forward" means +y |
| `test_goto_square_comes_back` | Four sides of a 1 m square end within 20 cm of the start |
| `test_goto_refused_on_the_ground_and_during_takeoff` | Goto is refused on the ground and during takeoff |
| `test_goto_refused_without_odometry` | Goto is refused when there's no odometry |
| `test_goto_aborts_when_odometry_stops` | If odometry is lost mid-move, the goto aborts and the drone holds |
| `test_goto_timeout` | A goto that can't arrive in time aborts and holds |
| `test_cancel_goto_holds` | Cancelling a goto holds in place |
| `test_goto_feedback` | The goto reports the distance remaining while moving |

**Land and hold**

| Test | What it checks |
| --- | --- |
| `test_land_preempts_goto` | Land interrupts a goto (which aborts) and lands successfully |
| `test_land_cannot_be_cancelled` | A landing can't be cancelled |
| `test_land_refused_on_the_ground` | Land is refused when already on the ground |
| `test_hold_corrects_sag` | Hold corrects a slow sink and stays within 2 cm of target |
| `test_tilt_correction` | Height = range × cos(tilt): 2.0 m at 60° gives 1.0 m |
| `test_minus_inf_is_the_ground` | A range of −inf is treated as height 0 |

**Rangefinder loss**

| Test | What it checks |
| --- | --- |
| `test_range_lost_hovers_then_resumes_hold` | Losing the range commands zero velocity; when it returns, the drone holds again |
| `test_range_lost_aborts_goto` | Losing the range aborts a goto |
| `test_range_lost_too_long_lands_blind` | If the range is lost for too long, the drone lands without it and odometry detects touchdown |
| `test_land_goal_during_autonomous_landing` | A Land request during that blind landing succeeds |
| `test_range_lost_on_the_ground_during_takeoff_stays_grounded` | If the range is lost before liftoff, the drone stays on the ground and never climbs without a goal |
| `test_range_lost_mid_takeoff_holds_the_height_reached` | If the range is lost mid-climb, the drone holds the height reached and doesn't climb further |

**Radio override**

| Test | What it checks |
| --- | --- |
| `test_override_aborts_the_goal_and_goes_quiet` | When the radio takes over, the current goal aborts and the mission stops publishing |
| `test_goals_refused_while_overridden` | Takeoff, Goto and Land are all refused while overridden |
| `test_control_back_in_the_air_holds_where_it_is` | When control comes back, the drone holds where the pilot left it, not at the old target |
| `test_control_back_on_the_ground_stays_grounded` | If the pilot landed, the drone stays grounded when control comes back |
| `test_override_during_land_aborts_it` | An override during landing aborts the landing |
| `test_repeated_control_messages_change_nothing` | Repeated control messages cause no extra state changes |

**Arming**

| Test | What it checks |
| --- | --- |
| `test_takeoff_refused_until_armed` | Takeoff is refused until armed |
| `test_takeoff_refused_before_any_status` | Takeoff is refused before any `fc/status` has arrived (armed state unknown) |
| `test_without_radio_arming_takeoff_needs_no_arm` | With `radio_arms=false`, the node arms the drone itself |
| `test_stale_disarmed_status_does_not_abort_takeoff` | An old "disarmed" status that arrives late doesn't abort the takeoff |
| `test_disarm_in_the_air_aborts_and_goes_quiet` | Disarming in flight (the kill switch) aborts the goal, goes GROUNDED and stops publishing |
| `test_disarm_on_the_ground_changes_nothing` | Disarming on the ground changes nothing |

## 1.6 `drone_safety/test/test_arbiter.py` (9 tests, João Barros)

Tests which command source reaches fc_bridge (`arbiter.py`), without ROS. Priority is radio > manual > mission, with a 0.3 s timeout.

| Test | What it checks |
| --- | --- |
| `test_nothing_active_at_start` | No source is active at start, and there's no change to report |
| `test_single_source_is_forwarded` | A single source (mission) is forwarded |
| `test_radio_takes_over_from_mission` | The radio takes over, and mission commands are dropped while the radio is active |
| `test_manual_beats_mission_but_not_radio` | Manual beats mission but loses to the radio |
| `test_control_returns_when_the_radio_goes_quiet` | When the radio is silent for more than 0.3 s, mission is forwarded again |
| `test_everything_quiet_is_none` | With no fresh source at all, nothing is active |
| `test_unknown_source_is_never_forwarded` | An unknown source ("keyboard") is never forwarded |
| `test_update_reports_changes_once` | A change of active source is reported exactly once |
| `test_time_going_backwards_is_not_fresh` | If the clock jumps back (sim reset), old commands don't count as fresh |

## 1.7 `drone_basics_py/test/test_radio_teleop.py` (24 tests, João Barros)

Tests the radio handling in `radio_teleop` by feeding it Joy messages directly. No radio and no launch are needed.

| Test | What it checks |
| --- | --- |
| `test_switch_off_publishes_nothing` | With the arm switch off, sticks publish nothing |
| `test_engage_after_hold` | The arm switch held for 0.1 s engages control |
| `test_no_engage_before_hold` | Control doesn't engage before 0.1 s |
| `test_bounce_while_arming_does_not_engage` | A burst of switch bounce (recorded with `arm_bounce.py`) doesn't engage |
| `test_engages_once_bounce_settles` | The hold time counts from the last bounce, not the first |
| `test_off_is_immediate` | Switching off releases control immediately |
| `test_bounce_while_disarming_does_not_reengage` | Bounce while switching off doesn't re-engage |
| `test_engage_refused_with_throttle_off_centre` | Control doesn't engage unless the throttle is centred |
| `test_throttle_moves_freely_once_engaged` | Once engaged, the throttle can move freely (full stick gives +0.3 m/s) |
| `test_sticks_scaled_to_limits` | Full stick maps to the limits (0.5 m/s horizontal, 0.3 m/s vertical, 1.0 rad/s yaw) in frame `base_link` |
| `test_deadband_gives_zero` | Small stick movements inside the deadband give zero |
| `test_reengage_needs_throttle_centred_again` | Re-engaging needs the throttle centred again |
| `test_switch_at_threshold_is_off` | A switch value exactly at the 0.5 threshold counts as off |
| `test_missing_arm_axis_is_off` | A Joy message without the arm axis counts as off |
| `test_arm_switch_arms_the_fc_once` | The arm switch calls `fc/arm(true)` exactly once |
| `test_arm_switch_off_disarms_even_in_flight` | Switching arm off calls `fc/arm(false)` even mid-flight (the kill switch) |
| `test_arm_switch_on_at_start_must_be_cycled` | A switch already on at start must be turned off and on again before it arms, as INAV requires |
| `test_arming_refused_with_throttle_off_centre` | Arming is refused unless the throttle is centred |
| `test_arm_alone_does_not_take_over` | With a separate takeover switch, arming alone doesn't take control |
| `test_takeover_alone_does_nothing` | The takeover switch alone, without arm, does nothing |
| `test_takeover_with_arm_on_engages_after_hold` | Arm + takeover engages after the hold, counted from the takeover switch |
| `test_takeover_off_releases_at_once` | Takeover off releases control immediately |
| `test_arm_off_releases_even_with_takeover_on` | Arm off releases control and disarms, even with takeover still on |
| `test_missing_takeover_axis_is_off` | A Joy message without the takeover axis counts as off |

## 1.8 `drone_sim_sensors/test/test_flow_model.py` (11 tests, David Roque)

Tests the simulated optical flow sensor math (`flow_model.py`), without ROS.

| Test | What it checks |
| --- | --- |
| `test_hover_gives_no_flow` | Hovering gives zero flow |
| `test_forward_gives_negative_flow_y` | Moving forward gives negative flow Y (sign convention) |
| `test_left_gives_positive_flow_x` | Moving left gives positive flow X |
| `test_rotation_in_place_equals_body_rate` | Rotating in place gives flow equal to the body rotation rate |
| `test_tilt_lengthens_the_distance` | Tilt lengthens the distance to the ground, which reduces the flow |
| `test_unusable_geometry_gives_none` | On the floor (height 0) or on its side, there's no result |
| `test_whole_degrees_truncate_toward_zero` | Values are truncated to whole degrees per second, as INAV's MSP sends them |
| `test_measure_passes_ideal_flow_when_clean` | With no noise, quality is 255 and the flow is exact |
| `test_measure_too_low_has_no_quality` | Below 8 cm the quality is 0 |
| `test_measure_too_fast_has_no_quality` | Above 7 rad/s the quality is 0 |
| `test_noise_has_the_requested_spread` | Over 4000 samples, noise has mean ≈ 0 and the requested standard deviation (±10 %) |

## 1.9 Lint and style checks

| Package | Checks |
| --- | --- |
| `drone_basics_py`, `drone_mission`, `drone_safety` | flake8, pep257, mypy, xmllint, copyright (the copyright check is skipped) |
| `drone_sim_sensors` | flake8, pep257, copyright (skipped). **mypy and xmllint are missing** |
| `drone_basics_cpp`, `drone_bringup` | `ament_lint_common` (cppcheck, uncrustify, lint_cmake, xmllint, flake8 and pep257 on the launch files) |
| `drone_fc_bridge` | **No lint at all.** The main C++ node isn't style-checked |
| `telemetry/` (CI job `telemetry-python`) | Syntax check and flake8. **No tests** |

## 1.10 What has no tests

| Code | Status |
| --- | --- |
| `telemetry/inav_telemetry.py`, `telemetry/latency_test.py` | No tests: MSP framing, checksum and decoders are all untested |
| `drone_safety/safety_manager.py` (the ROS node) | The arbiter logic is tested, but not the node: its topics `cmd/*` → `fc/setpoint_velocity` and `safety/active_source` |
| `drone_mission/mission.py` (the ROS node) | The logic is tested, but not the Takeoff, Goto and Land action servers over ROS |
| `drone_mission/demo_flight.py`, `drone_basics_py/setpoint_pub.py` | Nothing |
| `drone_sim_sensors/flow_model.py` (the ROS node) | The math is tested, but not the node publishing `fc/optical_flow` |
| `drone_basics_cpp/watchdog.cpp` | Nothing |
| `drone_bringup/launch/*.py`, `config/*.yaml` | Nothing: a broken launch file or a mismatched config value passes CI |
| Gazebo simulation | Not in CI at all: CI doesn't install Gazebo |
| `fc_bridge` with the `sim.yaml` parameters | Only tested with its built-in defaults |

---

# Part 2: tests to add

Each block lists where the test goes, what it checks, and what it would catch. They're grouped by area and ranked by value within each group.

## A. Telemetry and INAV (`telemetry/`)

`telemetry/` isn't a ROS package, so these tests are plain pytest. Put them in `telemetry/tests/` and add to CI job `telemetry-python`:

```yaml
      - name: Unit tests
        run: |
          pip install pytest
          pytest telemetry -v
```

### A1. MSP framing: `telemetry/tests/test_msp_frame.py`

| Test | Checks |
| --- | --- |
| `test_crc_known_frames` | `crc8_dvb_s2` gives the CRC byte of real frames from the captures, e.g. `24583e0001000300000205a6` (MSP_API_VERSION): the CRC over bytes 3 to −1 equals `0xa6` |
| `test_build_frame_layout` | `build_frame(cmd, payload)` = `$X<` + flag 0 + command (little-endian u16) + size (u16) + payload + CRC, for both an empty payload and a non-empty one |
| `test_build_frame_v2_command_ids` | Commands above 255 (0x2000, 0x2001, 0x2002) are encoded in 2 bytes |
| `test_parser_reads_split_frames` | `MSPClient._next_frame`, with a fake socket that delivers one frame in 3 pieces, still returns the full frame |
| `test_parser_skips_garbage` | Junk bytes before `$X` are skipped |
| `test_parser_rejects_bad_crc` | A frame with one flipped byte is rejected, not decoded |
| `test_parser_error_frame` | An error reply (`$X!`) is reported as an error, not as data |
| `test_request_timeout` | When the fake socket never answers, `request` returns within its timeout and doesn't hang |

**Catches:** a broken checksum or parser, which would silently corrupt every telemetry value.

> `latency_test.py` has its own copy of `crc8_dvb_s2` and `build_frame`. Either move both copies into one shared `msp.py` that both scripts import, or add a test that both copies give identical bytes.

### A2. Decoders with hand-made payloads: `telemetry/tests/test_decoders.py`

Build each payload with `struct.pack` and check the decoded values and units:

| Test | Checks |
| --- | --- |
| `test_attitude_units` | MSP_ATTITUDE: roll and pitch are sent in tenths of a degree (450 → 45.0°), heading in degrees |
| `test_altitude_units` | Altitude: centimetres → metres, vario sign |
| `test_analog_battery` | Voltage and current scaling (e.g. 162 → 16.2 V for MSP_ANALOG; check the scaling used by MSP2_INAV_ANALOG) |
| `test_raw_imu` | Accelerometer and gyro axes in the right order |
| `test_opflow` | `d_opflow`: quality and the four signed rates; negative values survive |
| `test_raw_gps` | lat/lon ÷ 1e7, fix and satellite count |
| `test_arming_fields` | Each bit of the arming flags maps to the right name (`ARMING_BITS`) |
| `test_flight_modes` | With `MODE_NAMES` from a box-names reply, bit 17 → `FAILSAFE` (as in the captures) |
| `test_sensor_fields` | `0xa3` → acc, baro, optical flow, temperature; **rangefinder not present** |
| `test_short_payload` | A payload one byte too short raises a clear error or is marked invalid, and doesn't crash the poll loop |

**Catches:** wrong units or scaling: a 10× attitude error, metres vs centimetres, a wrong sign on flow.

### A3. Replay of real drone captures: `telemetry/tests/test_captures.py`

The INAV-4 branch (`issue123/INAV-4`) has `telemetry/inav/captures/.../*.jsonl`, real MSP replies from the drone. Its README says they were captured "for testing the decoders". Merge that branch, then:

| Test | Capture | Checks |
| --- | --- | --- |
| `test_every_ok_frame_has_valid_crc` | all | Every `ok: true` frame passes the CRC check, and every `ok: false` frame is rejected |
| `test_flat_still_attitude` | `flat_still` | Roll between −2° and 0°, pitch about −6°, battery about 16.2 V, acc Z about +507 |
| `test_radio_off_failsafe` | `radio_off` | The active mode is FAILSAFE, and the arming blockers include RC link, prearm and calibrating |
| `test_tilted_roll` | `tilted` | Roll 44–48°, the "not level" arming blocker is set, and the accelerometer agrees (Y ≈ Z) |
| `test_flow_moving` | `flow_moving` | Flow X reaches ≥ 40 °/s at some point, and quality is 100 most of the time |
| `test_sonar_zero_is_invalid` | any | The rangefinder isn't in the sensor mask, so the 0 cm reading must be reported as invalid, not as 0 m |
| `test_decoder_never_crashes` | all | Every frame in every file decodes without an exception |

**Catches:** decoder changes that break on real firmware data (INAV 9.1.0). These tests are much stronger than hand-made payloads because they're the exact bytes the drone sends.

### A4. Poll loop: `telemetry/tests/test_poll.py`

Use a fake MSP client that returns canned replies:

| Test | Checks |
| --- | --- |
| `test_rejected_message_is_dropped` | A command the flight controller answers with an error is removed from the poll list after the first cycle, as the module docstring promises |
| `test_one_json_object_per_cycle` | `--info` output: each line is valid JSON with the expected keys |
| `test_log_file_is_jsonl` | `--log` writes JSON Lines even in `--read` mode |
| `test_timeout_does_not_stop_the_loop` | One timed-out message doesn't stop the others from being polled |

### A5. Against real INAV firmware: INAV SITL (new CI job, run nightly)

INAV can be built as **SITL**, a program that runs the real flight-controller firmware on Linux with MSP on TCP port 5760. `inav_telemetry.py` already talks MSP over TCP, so it can connect to the simulator exactly as it connects to the ESP bridge.

Job outline:
1. Build INAV SITL for the same version as the drone (9.1.0). Cache the build.
2. Start it in the background.
3. `python3 telemetry/inav_telemetry.py --host 127.0.0.1 --port 5760 --info` for ~5 s, saving the output.
4. Check: the API version reply arrives, the FC variant is `INAV`, the version is 9.1.x, and attitude, status and analog are all present on every cycle, with no rejected core messages.
5. Optional: load `docs/extras/Drone_INAV_Backup_26_10_26.txt` into the SITL through the CLI, then check that box names and modes match the real drone's config.

**Catches:** MSP protocol changes after an INAV upgrade, messages your code polls that the firmware no longer supports, and a broken TCP client. This is as close to the real flight controller as CI can get without the drone.

### A6. Real drone check (manual, not CI)

The real flight controller can't be reached from GitHub's machines. Turn the bench checks into a script, `telemetry/bench_check.py`, that connects to the drone and runs the A3 checks live, and log its result with `logbook.py`. Run it before each flight session. The INAV-4 branch's `msp_inventory.py` is already most of the way there.

### A7. The Python decoders where fc_bridge's C++ decoders disagree (done)

ROS-6 step A on `main` added C++ decoders for fc_bridge (`drone_fc_bridge/src/inav_decode.cpp`), written from the INAV 9.1.0 source. Their comments name three bugs in `inav_telemetry.py`: arming blockers include the simulator and unused bits; 0 cm from the rangefinder counts as a valid distance; power and the drawn counters are read unsigned. Each is now a strict expected fail at the end of `telemetry/tests/test_decoders.py`, replacing `test_unknown_arming_bit_is_kept`, which expected the wrong arming behaviour. Two passing rangefinder tests were added too (it had none). Details: [TESTS.md](../TESTS.md#33-test_decoderspy-decoders-59-cases-3-expected-fail).

### A8. The C++ tests' copies of the recordings match (done)

`drone_fc_bridge/test/data/` on `main` holds copies of the four recordings. `telemetry/tests/test_capture_copies.py` checks that every file under `ros2_ws/src` with a recording's name is identical to the original, and prints the `cp` command if not. It skips until `main` is merged into this branch.

## B. Drone limits and configuration

### B1. Config consistency: `drone_bringup/test/test_config.py`

Plain pytest that loads `config/sim.yaml`. Register it in `drone_bringup/CMakeLists.txt` with `ament_add_pytest_test`, and add `ament_cmake_pytest` as a test dependency.

| Test | Rule (source) |
| --- | --- |
| `test_mission_vz_equals_fc_limit` | `mission.max_vz == fc_bridge.max_speed_z` (the comment says "= fc_bridge max_speed_z") |
| `test_safety_timeout_equals_fc_timeout` | `safety_manager.source_timeout_s == fc_bridge.setpoint_timeout_s` (the comment says "keep equal") |
| `test_mission_speed_within_fc_limit` | `mission.speed ≤ max_speed_xy` and `mission.yaw_rate ≤ max_yaw_rate`, otherwise fc_bridge clamps the mission silently |
| `test_land_speed_within_fc_limit` | `mission.land_speed ≤ max_speed_z` |
| `test_radio_limits_within_fc_limits` | `radio_teleop.max_xy/max_z/max_yaw ≤` the fc_bridge limits |
| `test_target_height_inside_rangefinder` | `range_min < mission.ground_h < mission.target_h < range_max` |
| `test_demo_height_inside_rangefinder` | `demo_flight.height < range_max` |
| `test_flow_min_height_above_ground_reading` | `flow_model.min_height` vs `mission.ground_h`: flow is usable before the drone counts as airborne |
| `test_all_timeouts_positive` | Every `*_timeout_s` and `rate_hz` value is > 0 |
| `test_priority_has_radio_first` | `safety_manager.priority[0] == 'radio'`: the pilot must always win |
| `test_every_yaml_node_exists` | Every top-level key in the YAML is a node name used in `sim.launch.py`, which catches typos that silently ignore parameters |

**Catches:** someone raises one limit in one place but not the other, and the drone behaves differently from what the mission expects.

### B2. fc_bridge with the real sim config: `drone_fc_bridge/test/test_sim_config.py`

A launch test like `test_state.py`, but it starts fc_bridge with `parameters=[sim.yaml]` (noise set to 0 on top):

| Test | Checks |
| --- | --- |
| `test_range_limits_are_mtf02p` | `fc/range` reports min 0.02 and max 6.0, the sensor that actually flies in the sim, not the 0.04/4.0 defaults |
| `test_range_at_5m_is_valid` | 5 m is valid with the MTF-02P (it's +inf with the defaults) |
| `test_narrow_cone` | With a 4° cone, tilt behaves as configured |
| `test_clamps_from_yaml` | The clamps equal the YAML values |

Also decide whether fc_bridge's code defaults should change to the MTF-02P, so that `test_state.py` and the toy drone in `test_logic.py` (0.04–4.0 m) match the real sensor.

### B3. fc_bridge parameter safety: add to `test_failsafes.py`, or a new launch test

| Test | Checks |
| --- | --- |
| `test_bad_backend_exits` | `backend:=foo` makes the process exit with an error instead of running |
| `test_combined_clamp` | All axes over their limits at once are each clamped, and the horizontal direction is kept |
| `test_rate_is_respected` | The output rate is 20 Hz ± 10 % over 3 s |
| `test_timeout_recovers` | After a timeout, a new setpoint is followed again |
| `test_old_stamped_setpoint` | Decide whether a setpoint whose header stamp is already older than the timeout is rejected, then test it |

## C. ROS nodes running together (launch tests, every PR, no Gazebo)

These tests are the missing middle layer. The logic is tested and fc_bridge is tested, but no test checks that the nodes are connected correctly.

### C1. `drone_safety/test/test_safety_manager_node.py`

Starts `safety_manager`. The test publishes on `cmd/mission`, `cmd/manual` and `cmd/radio`, and reads `fc/setpoint_velocity` and `safety/active_source`.

| Test | Checks |
| --- | --- |
| `test_mission_forwarded` | A command on `cmd/mission` comes out unchanged |
| `test_radio_wins` | With mission and radio both publishing, only the radio values come out, and `active_source` = `radio` |
| `test_radio_quiet_returns_to_mission` | After the radio has been silent for 0.3 s, mission is forwarded again |
| `test_active_source_is_latched` | A subscriber that starts late still receives the current source |
| `test_low_battery_warns` | A `fc/battery` message below 20 % logs a warning (the behaviour is currently a placeholder) |

### C2. Full stack without Gazebo: `drone_bringup/test/test_stack_fake_plant.py` ⭐

Starts **mission + safety_manager + fc_bridge** with `sim.yaml`. The test node acts as a simple drone: it subscribes to `/X3/gazebo/command/twist`, integrates the velocity, and publishes `/X3/odom` at 50 Hz. fc_bridge turns that into `fc/range` and `fc/odom` itself.

| Test | Checks |
| --- | --- |
| `test_takeoff_action` | Sending the `Takeoff` action succeeds, and the fake drone is at 1.2 ± 0.05 m |
| `test_goto_action` | `Goto(1, 0)` succeeds, and the drone is ~1 m forward |
| `test_land_action` | `Land` succeeds, the height is below `ground_h`, and the mission stops publishing |
| `test_radio_override_over_ros` | Publishing on `cmd/radio` mid-goto aborts the goal with "overridden by radio" |
| `test_stop_mission_node_stops_drone` | Killing the mission node makes the drone's velocity return to 0 within 0.3 s + margin |
| `test_disarm_stops_everything` | `fc/arm(false)` mid-flight sends zero to the sim and puts the mission in GROUNDED |

**Catches:** wrong topic names, remaps, QoS, action names or parameter loading. None of these is caught today. The test is fast (seconds) and needs no Gazebo, so it can run on every PR. **This is the most valuable new ROS test.**

### C3. `drone_basics_py/test/test_radio_teleop_node.py`

Starts `radio_teleop` with `sim.yaml` (the real axis signs). The test publishes `/joy` and provides a fake `fc/arm` service.

| Test | Checks |
| --- | --- |
| `test_real_axis_signs` | With the real signs, pitch stick up gives +x, throttle up gives +z, roll right gives −y |
| `test_arm_service_called` | Arm switch on → `fc/arm(true)`; off → `fc/arm(false)` |
| `test_publishes_on_setpoint_velocity` | Output is on the topic the launch remaps to `cmd/radio` |

### C4. `drone_sim_sensors/test/test_flow_node.py`

Starts `flow_model` (noise 0, quantize off). The test feeds odometry and range.

| Test | Checks |
| --- | --- |
| `test_publishes_flow` | `fc/optical_flow` is published at the input rate |
| `test_forward_motion` | Forward motion gives negative flow Y over ROS |
| `test_low_height_quality_zero` | Below 8 cm the quality is 0 |
| `test_seed_is_reproducible` | The same seed gives the same noise sequence |

Also add `test_mypy.py` and `test_xmllint.py` to this package, as the other Python packages have.

### C5. `drone_basics_cpp`: watchdog

A launch test that checks the warning appears after `timeout_s` with no setpoint, and doesn't appear while setpoints arrive at 20 Hz. Also run `setpoint_pub` for 2 s and check it publishes at 20 Hz with the configured speed.

### C6. Launch files: `drone_bringup/test/test_launch_files.py` (done)

Done as planned, for all 48 argument combinations, plus: the clock (`use_sim_time`) per backend, `sim.yaml` given to every node, the pre-start package check covering every package started, and the guard against a second sim. 24 cases, about 1 s. Details: [TESTS.md](../TESTS.md#42-what-the-launch-file-starts-test_launch_filespy-24-cases). The original plan:

Without running anything, build the launch description for each combination of arguments and inspect it:

| Combination | Checks |
| --- | --- |
| `backend:=sim radio:=true` | It includes Gazebo, `ros_gz_bridge`, `flow_model`, `fc_bridge`, `safety_manager`, `mission`, `joy_node` and `radio_teleop` |
| `backend:=inav` | It includes **no** Gazebo, no `ros_gz_bridge` and no `flow_model` |
| `radio:=false` | No `joy_node`, and the mission has `radio_arms=false` |
| `demo:=true` | `demo_flight` is included |
| `source:=setpoint` | `setpoint_pub` is included instead of the mission |
| All | Every `package`/`executable` named exists in the ament index, and every `parameters=` file exists |

**Catches:** a renamed executable or wrong path, which today is only found when someone launches the sim.

### C7. The Gazebo worlds: `drone_bringup/test/test_worlds.py` (done)

Reads every world in `drone_bringup/worlds/` and the default world as XML, without Gazebo: the drone is there, its velocity controller and odometry use the topics in `gz_bridge.yaml`, it starts on the ground, its Fuel model is pinned, and every model, texture and mesh exists and is installed. It is the cheap half of D2, on every PR. It does little in CI until `feature/153` brings `worlds/`, because the default world is Gazebo's own and CI has no Gazebo. Details: [TESTS.md](../TESTS.md#43-the-gazebo-worlds-test_worldspy-9-cases).

## D. Simulation in Gazebo (new CI job: nightly, and from the Actions tab)

### D0. What's needed first (done)

1. `headless:=true` in `sim.launch.py`: `gz_args = '-s -r ' + world`, server only, no window. Not `--headless-rendering`: nothing in these worlds renders, and in the dev container that option tries the GPU without its driver and Gazebo never starts. A world with a camera would need it.
2. The job runs **inside the project's Docker image** (`seame/ros2-dev:jazzy`), the same sim as on our laptops. `.github/workflows/nightly.yml` builds it from the `docker-image` job's layer cache, then runs `seame-docker/scripts/sim_flight_test.sh`, which anyone can also run on the host.
3. It runs every night (02:00 UTC), from the Actions tab, and on PRs that change the sim (launch, config, the test, the script). It takes 4–5 min and isn't part of `block-red-pr`.

### D1. Flight tests in Gazebo: `drone_bringup/test/test_sim_flight.py` (done)

A launch test that includes `sim.launch.py headless:=true radio:=false` (own `ROS_DOMAIN_ID`, localhost only, own `GZ_PARTITION`). One flight, in order; after a failed step the rest are skipped. Every check uses Gazebo's ground truth (`/sim/ground_truth`). Not registered with colcon, so PR CI never runs it (only its lint).

| Step | Checks | Pass if | Measured |
| --- | --- | --- | --- |
| `test_1_sim_comes_up` | Ground truth, `fc/status`, `fc/range`, the action servers, sim time | All within 180 s (the first run downloads the X3 from Fuel); backend `sim` | about 3 s |
| `test_2_on_the_ground_at_start` | The drone is on the ground | Height and `fc/range` < `ground_h`; still; upright | z 0.054 m |
| `test_3_takeoff` | `Takeoff` to `target_h` | SUCCEEDED; true height and rangefinder 1.2 ± 0.1 m | 1.16–1.18 m |
| `test_4_hover_drift` | 3 s to settle, then hold 10 s | No overshoot above 1.3 m; drift < 0.1 m; height 1.2 ± 0.05 m | drift 0.000 m, 1.196–1.204 m |
| `test_5_square` | The demo's square: 1 m forward, quarter turn left, 4 times | Sides 1 ± (`pos_tolerance` + 0.1) m; turns 90° ± (`yaw_tolerance` + 0.02); closes < 0.3 m; heading within 4 turn tolerances | sides 0.87–0.94 m, turns 88–91°, closes 0.085 m |
| `test_6_speed_capped_at_the_limit` | A Goto asking 2 m/s, and speeds since takeoff | Reaches > 80 % of `max_speed_xy`, never > limit + 10 %; z and yaw rate too; fc_bridge never sends over a limit | 0.459 m/s, z 0.300 m/s |
| `test_7_land` | `Land` | SUCCEEDED; back on the ground; upright; the mission disarms | z 0.055 m |
| `test_8_mission_dies_and_the_drone_stops` | Take off again, kill the mission node (SIGKILL) mid-Goto, then land by hand on `cmd/manual` | Stopped (< 0.05 m/s) within `setpoint_timeout_s` + 1 s; coasts < 0.5 m; holds height; lands; disarms | 1.07 s, 0.228 m |

Not done yet: `test_flow_matches_motion` (flow sign and size against Gazebo's velocity ÷ height).

Every run keeps the test log, the xUnit report, every node's log and a rosbag of the flight (`ros2 bag play flight_bag`) as the `sim-flight` artifact.

**Known failure today:** the mission node's commands stall for up to 0.8 s (rclpy's multi-threaded executor), so fc_bridge times out every 1–2 s and Goto aborts with "rangefinder lost" or is rejected. The flight fails at the square on most runs until that's fixed. With the mission on the single-threaded executor and `await` in `execute()`, it passed with no timeouts.

### D2. Run it for every world

Run D1 for each world: the default one and `outdoor_field.sdf` (from branch `feature/153`, once merged), plus any room world from `sim_room`. This checks that each world loads and the drone can fly in it.

### D3. Radio in the simulation

Publish fake `/joy` messages, as the real radio would send, into the full sim: engage the takeover mid-mission, check the mission aborts, check the stick moves the drone, release, and check the drone holds.

## E. CI improvements

| # | Change | Why |
| --- | --- | --- |
| E1 | Add `pytest` to job `telemetry-python` | Needed for part A |
| E2 | Add `ament_lint_auto` to `drone_fc_bridge` | The main C++ node has no lint |
| E3 | Add `test_mypy`/`test_xmllint` to `drone_sim_sensors` | It has fewer checks than the other Python packages |
| E4 | Add `shellcheck seame-docker/scripts/*.sh` | The scripts are never checked |
| E5 | Add flake8 on `seame-docker/ros2_ws/tools/` and `seame-docker/scripts/*.py` | These aren't covered by any job |
| E6 | Add coverage: `colcon test --pytest-with-coverage` and upload the report | Shows which lines are never tested |
| E7 | Add a `sim-nightly` job (part D) with `schedule:` and `workflow_dispatch:` | Gazebo tests without slowing PRs |
| E8 | Add a `inav-sitl` job (A5), nightly | Real firmware protocol check |
| E9 | Make the jobs **required status checks** on `main` (GitHub settings → Branches) | Otherwise a red CI can still be merged |
| E10 | Remove `Develop` from the triggers | The branch was deleted (Nov 12); `ci.yml` still lists it |
| E11 | ~~Before merging `tsk/re-estructure`, check it doesn't delete tests~~ | The branch was deleted without being merged (Nov 12) |

---

# Order of work

| Step | Work | Effort | CI cost |
| --- | --- | --- | --- |
| 1 | **B1** config consistency + **E1** pytest in the telemetry job | Small | +seconds |
| 2 | **A1 + A2** MSP framing and decoders | Small | +seconds |
| 3 | Merge INAV-4 → **A3** capture replay | Small | +seconds |
| 4 | **C2** full stack with a fake drone ⭐ | Medium | +~30 s |
| 5 | **B2** fc_bridge with `sim.yaml`, **C6** launch files (done), **C7** worlds (done) | Small | +~20 s |
| 6 | **C1, C3, C4** node tests, **E2–E5** lint | Medium | +~1 min |
| 7 | **D0 + D1** Gazebo flight tests, nightly | Large | Nightly only |
| 8 | **A5** INAV SITL, nightly | Medium/large | Nightly only |
| 9 | **E9** required checks | Settings only | — |

Steps 1–3 cover telemetry, INAV and the drone limits with fast tests that run on every PR. Step 4 checks that the whole ROS stack works together. Steps 7–8 test the real simulator and the real INAV firmware.
