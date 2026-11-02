# Test report: `staging` after merging `test`

Run on Nov 2, 2026, on commit `ed2219d` (staging with test merged in). Produced from the test result files (xUnit/JUnit XML) and the console log of that run, not typed by hand.

## Result

**123 test cases: 119 passed, 4 skipped, 0 failed.** The build had no errors and every package's tests exited 0.

| | Test cases | Passed | Skipped | Failed |
| --- | --- | --- | --- | --- |
| Behaviour tests (what the code does) | 99 | 99 | 0 | 0 |
| Lint and style checks | 24 | 20 | 4 | 0 |
| **Total** | **123** | **119** | **4** | **0** |

**About "135 tests":** `colcon test-result` prints `Summary: 135 tests, 0 errors, 0 failures, 4 skipped`. That number counts the 12 CTest entries of the C++ packages (one per test file or linter) *and* the test cases inside them, so some tests are counted twice. The 123 above counts each test case once.

## How it was run

The same commands as the CI workflow (`.github/workflows/ci.yml`), from a clean build directory so nothing left over from earlier builds could hide a problem:

```bash
cd ~/ros2_ws
colcon build --event-handlers console_direct+
source install/setup.bash
colcon test --event-handlers console_direct+
colcon test-result --verbose
```

| Item | Value |
| --- | --- |
| Where | The team dev container (`seame/ros2-dev:jazzy`), on a 4-core laptop. Build and install in `/tmp/ci`, so the workspace's own `build/` and `install/` were not touched |
| ROS / OS / Python | jazzy / Ubuntu 24.04.5 LTS / 3.12.3 |
| Build | exit code 0, 44 s, 7 packages |
| Tests | exit code 0, 43 s |
| Domain | The `fc_bridge` launch tests run on `ROS_DOMAIN_ID=199`, localhost only, so a running sim can't interfere |

Not the same as CI: CI starts from the plain `ros:jazzy` image and installs only build and test dependencies. The dev container has more installed (Gazebo, the joystick driver). The container image predates the camera packages that came with the merge; no test uses them. CI will run on the pull request into `test`.

## By package

| Package | What is tested | How | Behaviour | Lint | Skipped | Time |
| --- | --- | --- | --- | --- | --- | --- |
| `drone_fc_bridge` | Failsafes (timeout, NaN, clamp), state shaped like flow + rangefinder, arm/hold/status services, the `inav` stub | launch_testing (real node, fake inputs) | 23 | 0 | 0 | 40.5 s |
| `drone_mission` | The flight logic: takeoff, goto, land, range lost, overrides, arming | pytest, no ROS | 43 | 5 | 1 | 10.1 s |
| `drone_safety` | Command arbitration: radio > manual > mission | pytest, no ROS | 9 | 5 | 1 | 11.9 s |
| `drone_basics_py` | `radio_teleop`: arm and takeover switches, debounce, sticks | pytest, node without spinning | 24 | 5 | 1 | 12.9 s |
| `drone_bringup` | Lint of the launch files and package | ament linters | 0 | 5 | 0 | 1.36 s |
| `drone_basics_cpp` | Lint of the crash-course C++ nodes | ament linters | 0 | 4 | 1 | 2.61 s |

`drone_interfaces` has no tests of its own (message and action definitions); it builds, and the tests above use it.

## Every behaviour test

Times are as reported by each runner. The `fc_bridge` tests share one running node per file, so most of their time is in the file's setup; the per-test times show only the test itself. What each group checks in plain words is in the README's Tests table.

### `drone_fc_bridge` · `test_failsafes.py` (9)

| Test | Result | Time (s) |
| --- | --- | --- |
| `test_fresh_setpoint_is_forwarded` | pass | 1.821 |
| `test_horizontal_clamp_keeps_direction` | pass | 1.819 |
| `test_inf_is_rejected` | pass | 1.820 |
| `test_nan_is_rejected_and_times_out` | pass | 2.313 |
| `test_roll_and_pitch_rates_are_zeroed` | pass | 1.809 |
| `test_sim_enable_is_published` | pass | 2.311 |
| `test_timeout_sends_zero` | pass | 2.818 |
| `test_vertical_and_yaw_clamp` | pass | 2.831 |
| `test_zero_without_setpoints` | pass | 1.807 |

### `drone_fc_bridge` · `test_state.py` (7)

| Test | Result | Time (s) |
| --- | --- | --- |
| `test_body_velocity_rotated_by_heading` | pass | 1.528 |
| `test_height_and_orientation_from_sim` | pass | 0.419 |
| `test_position_is_integrated_not_copied` | pass | 1.527 |
| `test_range_level` | pass | 0.415 |
| `test_range_out_of_range_is_inf` | pass | 1.243 |
| `test_range_reads_longer_when_tilted` | pass | 0.413 |
| `test_velocity_passes_through` | pass | 0.612 |

### `drone_fc_bridge` · `test_services.py` (4)

| Test | Result | Time (s) |
| --- | --- | --- |
| `test_disarm_and_rearm` | pass | 3.021 |
| `test_hold_sends_zero_despite_setpoints` | pass | 1.528 |
| `test_starts_armed` | pass | 0.000 |
| `test_status_reports_setpoint_age` | pass | 1.450 |

### `drone_fc_bridge` · `test_inav.py` (3)

| Test | Result | Time (s) |
| --- | --- | --- |
| `test_arm_is_refused` | pass | 0.004 |
| `test_nothing_reaches_the_sim` | pass | 0.000 |
| `test_status_says_inav_and_disarmed` | pass | 0.002 |

### `drone_mission` · `test_logic.py` (43)

| Test | Result | Time (s) |
| --- | --- | --- |
| `test_starts_grounded_and_silent` | pass | 0.001 |
| `test_takeoff_hold_land` | pass | 0.003 |
| `test_takeoff_to_a_given_height` | pass | 0.002 |
| `test_takeoff_refused_without_range` | pass | 0.002 |
| `test_takeoff_refused_above_range_max` | pass | 0.001 |
| `test_takeoff_refused_in_the_air` | pass | 0.002 |
| `test_takeoff_timeout_lands` | pass | 0.003 |
| `test_cancel_takeoff_holds_where_it_is` | pass | 0.002 |
| `test_goto_forward` | pass | 0.003 |
| `test_goto_is_relative_to_heading` | pass | 0.004 |
| `test_goto_square_comes_back` | pass | 0.009 |
| `test_goto_refused_on_the_ground_and_during_takeoff` | pass | 0.001 |
| `test_goto_refused_without_odometry` | pass | 0.002 |
| `test_goto_aborts_when_odometry_stops` | pass | 0.002 |
| `test_goto_timeout` | pass | 0.004 |
| `test_cancel_goto_holds` | pass | 0.002 |
| `test_land_preempts_goto` | pass | 0.003 |
| `test_land_cannot_be_cancelled` | pass | 0.002 |
| `test_land_refused_on_the_ground` | pass | 0.001 |
| `test_hold_corrects_sag` | pass | 0.005 |
| `test_tilt_correction` | pass | 0.001 |
| `test_minus_inf_is_the_ground` | pass | 0.001 |
| `test_range_lost_hovers_then_resumes_hold` | pass | 0.002 |
| `test_range_lost_aborts_goto` | pass | 0.001 |
| `test_range_lost_too_long_lands_blind` | pass | 0.002 |
| `test_land_goal_during_autonomous_landing` | pass | 0.002 |
| `test_goto_feedback` | pass | 0.002 |
| `test_takeoff_refused_until_range_is_steady` | pass | 0.002 |
| `test_range_gap_restarts_the_steady_time` | pass | 0.002 |
| `test_range_lost_on_the_ground_during_takeoff_stays_grounded` | pass | 0.002 |
| `test_range_lost_mid_takeoff_holds_the_height_reached` | pass | 0.002 |
| `test_override_aborts_the_goal_and_goes_quiet` | pass | 0.002 |
| `test_goals_refused_while_overridden` | pass | 0.001 |
| `test_control_back_in_the_air_holds_where_it_is` | pass | 0.003 |
| `test_control_back_on_the_ground_stays_grounded` | pass | 0.003 |
| `test_override_during_land_aborts_it` | pass | 0.002 |
| `test_repeated_control_messages_change_nothing` | pass | 0.002 |
| `test_takeoff_refused_until_armed` | pass | 0.001 |
| `test_takeoff_refused_before_any_status` | pass | 0.001 |
| `test_without_radio_arming_takeoff_needs_no_arm` | pass | 0.001 |
| `test_stale_disarmed_status_does_not_abort_takeoff` | pass | 0.002 |
| `test_disarm_in_the_air_aborts_and_goes_quiet` | pass | 0.002 |
| `test_disarm_on_the_ground_changes_nothing` | pass | 0.001 |

### `drone_safety` · `test_arbiter.py` (9)

| Test | Result | Time (s) |
| --- | --- | --- |
| `test_nothing_active_at_start` | pass | 0.001 |
| `test_single_source_is_forwarded` | pass | 0.001 |
| `test_radio_takes_over_from_mission` | pass | 0.001 |
| `test_manual_beats_mission_but_not_radio` | pass | 0.001 |
| `test_control_returns_when_the_radio_goes_quiet` | pass | 0.001 |
| `test_everything_quiet_is_none` | pass | 0.001 |
| `test_unknown_source_is_never_forwarded` | pass | 0.001 |
| `test_update_reports_changes_once` | pass | 0.001 |
| `test_time_going_backwards_is_not_fresh` | pass | 0.001 |

### `drone_basics_py` · `test_radio_teleop.py` (24)

| Test | Result | Time (s) |
| --- | --- | --- |
| `test_switch_off_publishes_nothing` | pass | 0.124 |
| `test_engage_after_hold` | pass | 0.082 |
| `test_no_engage_before_hold` | pass | 0.016 |
| `test_bounce_while_arming_does_not_engage` | pass | 0.016 |
| `test_engages_once_bounce_settles` | pass | 0.018 |
| `test_off_is_immediate` | pass | 0.026 |
| `test_bounce_while_disarming_does_not_reengage` | pass | 0.019 |
| `test_engage_refused_with_throttle_off_centre` | pass | 0.016 |
| `test_throttle_moves_freely_once_engaged` | pass | 0.024 |
| `test_sticks_scaled_to_limits` | pass | 0.021 |
| `test_deadband_gives_zero` | pass | 0.019 |
| `test_reengage_needs_throttle_centred_again` | pass | 0.021 |
| `test_switch_at_threshold_is_off` | pass | 0.021 |
| `test_missing_arm_axis_is_off` | pass | 0.019 |
| `test_arm_switch_arms_the_fc_once` | pass | 0.019 |
| `test_arm_switch_off_disarms_even_in_flight` | pass | 0.027 |
| `test_arm_switch_on_at_start_must_be_cycled` | pass | 0.020 |
| `test_arming_refused_with_throttle_off_centre` | pass | 0.019 |
| `test_arm_alone_does_not_take_over` | pass | 0.016 |
| `test_takeover_alone_does_nothing` | pass | 0.015 |
| `test_takeover_with_arm_on_engages_after_hold` | pass | 0.018 |
| `test_takeover_off_releases_at_once` | pass | 0.018 |
| `test_arm_off_releases_even_with_takeover_on` | pass | 0.019 |
| `test_missing_takeover_axis_is_off` | pass | 0.015 |

## Lint and style checks

| Package | Check | Result |
| --- | --- | --- |
| `drone_basics_cpp` | `cppcheck` `src/watchdog.cpp` | skipped |
| `drone_basics_cpp` | `lint_cmake` `CMakeLists.txt` | pass |
| `drone_basics_cpp` | `uncrustify` `src/watchdog.cpp` | pass |
| `drone_basics_cpp` | `xmllint` `package.xml` | pass |
| `drone_basics_py` | `test_copyright` `test_copyright` | skipped |
| `drone_basics_py` | `test_flake8` `test_flake8` | pass |
| `drone_basics_py` | `test_mypy` `test_mypy` | pass |
| `drone_basics_py` | `test_pep257` `test_pep257` | pass |
| `drone_basics_py` | `test_xmllint` `test_xmllint` | pass |
| `drone_bringup` | `flake8` `flake8` | pass |
| `drone_bringup` | `lint_cmake` `CMakeLists.txt` | pass |
| `drone_bringup` | `pep257` `./launch/basics.launch.py` | pass |
| `drone_bringup` | `pep257` `./launch/sim.launch.py` | pass |
| `drone_bringup` | `xmllint` `package.xml` | pass |
| `drone_mission` | `test_copyright` `test_copyright` | skipped |
| `drone_mission` | `test_flake8` `test_flake8` | pass |
| `drone_mission` | `test_mypy` `test_mypy` | pass |
| `drone_mission` | `test_pep257` `test_pep257` | pass |
| `drone_mission` | `test_xmllint` `test_xmllint` | pass |
| `drone_safety` | `test_copyright` `test_copyright` | skipped |
| `drone_safety` | `test_flake8` `test_flake8` | pass |
| `drone_safety` | `test_mypy` `test_mypy` | pass |
| `drone_safety` | `test_pep257` `test_pep257` | pass |
| `drone_safety` | `test_xmllint` `test_xmllint` | pass |

## Skipped, and why

| Package | Test | Reason |
| --- | --- | --- |
| `drone_basics_cpp` | `src/watchdog.cpp` | Test Skipped due to cppcheck 2.13.0 performance issues |
| `drone_basics_py` | `test_copyright` | No copyright header has been placed in the generated source file. |
| `drone_mission` | `test_copyright` | No copyright header has been placed in the generated source file. |
| `drone_safety` | `test_copyright` | No copyright header has been placed in the generated source file. |

The three `test_copyright` skips are the ROS package template's own: it skips until the team adds a license header to every file. The `cppcheck` skip is done by ament itself on this cppcheck version (2.13), which it considers too slow. None of the four is a behaviour test.

## Warnings in the output

- `drone_basics_py`, `drone_mission` and `drone_safety`: pytest warns `This process ... is multi-threaded, use of fork() may lead to deadlocks in the child`, from `test_flake8` starting flake8's worker processes. Python 3.12 warns whenever a multi-threaded process forks; it doesn't affect the result.
- `fc_bridge` logs `Setpoint timeout: holding (zero velocity)` and similar during its tests: that is the behaviour under test, printed by the node.
- No compiler warnings in the build.

## Do the tests catch real bugs?

A test that passes no matter what proves nothing. Each group was checked by breaking the code on purpose, running the tests, and putting the code back. Recorded in `CHANGES.md`:

| Date | Broken on purpose | Tests that failed |
| --- | --- | --- |
| Oct 26 | `fc_bridge` timeout check | the timeout, NaN and infinity tests |
| Oct 26 | `radio_teleop` arm debounce disabled | 7 |
| Oct 27 | `fc/odom` copying Gazebo's x instead of integrating | the integration test |
| Oct 29 | `mission` altitude hold off | 9 |
| Oct 29 | "not moving down" touchdown off | the blind-landing test |
| Oct 29 | Goto velocity not turned into the body frame | the heading and square tests |
| Oct 29 | Land not preempting other goals | the preemption test |
| Oct 30 | `safety_manager` priority order reversed | the arbiter tests |
| Oct 30 | Taking over no longer arming (since replaced in step 7) | 2 |
| Oct 30 | Takeoff allowed while disarmed | 2 |
| Oct 30 | Disarm in the air ignored by `mission` | 1 |
| Oct 30 | Arm switch off not disarming | 2 |
| Oct 30 | Arming on a switch already on at start | 1 |
| Oct 30 | `inav` backend accepting `fc/arm` | 3 |

## What these tests don't cover

- **Gazebo.** No automated test runs the full sim: the `fc_bridge` tests replace Gazebo with fake messages, and the mission logic flies a toy model. Full flights were checked by hand in headless Gazebo (below). CI doesn't install Gazebo at all.
- **The real drone.** The `inav` backend is a stub; nothing talks MSP yet, so nothing here says anything about the real link.
- **The launch file.** Only linted. Its guard (missing package, second Gazebo) and the `backend` and `radio` arguments were checked by hand.
- **`fc_bridge` recovery after a timeout** has no test of its own (noted on issues #70 and #79).
- **Timing under load.** Tests run on an idle machine; command gaps under CPU load were seen in the sim (README known issues).

## Checked by hand in the sim (Oct 26–30)

| Date | What | Result |
| --- | --- | --- |
| Oct 27 | Circle flight, `fc/odom` against Gazebo's true pose | Same circle, `fc/odom` drifting about 0.5 m per minute from the truth; `fc/range` follows height |
| Oct 29 | `mission` demo: takeoff, 1 m square, land | Every goal succeeded; height 1.19–1.22 m; square sides 0.82–0.91 m; back within 0.09 m; disarmed |
| Oct 30 | Radio takeover with `ros2 topic pub` as the radio | Goto aborted `overridden by radio`; mission held after release, landed on request |
| Oct 30 | Launch guard | Missing package: fails before starting anything; second Gazebo in the same partition: refused |
| Oct 30 | Fake Pocket: arm, takeoff, SA off in the air | Takeoff refused until armed; SA off dropped it from 1.03 m; `mission` went to `grounded` |
| Oct 30 | `radio:=false` demo; `backend:=inav` | Demo flew by itself; `inav`: no Gazebo, `fc/arm` refused, Takeoff refused |
| Oct 30 | Real RadioMaster Pocket (João) | Takeover mid-Goto, release, re-arm, kill switch: all as expected |

## Console output (excerpts)

Each runner's own summary line, as printed. colcon tests packages in parallel, so the lines interleave: `13 passed, 1 skipped` is `drone_safety` (9 + 5 lint), `47 passed, 1 skipped` is `drone_mission` (43 + 5), `28 passed, 1 skipped` is `drone_basics_py` (24 + 5). Each `100% tests passed ... out of 4` is CTest for the package finishing on the next line: `drone_basics_cpp` (4 linters), `drone_fc_bridge` (4 launch test files), `drone_bringup` (4 linters).

```text
Starting >>> drone_interfaces
Starting >>> drone_basics_cpp
Starting >>> drone_basics_py
Starting >>> drone_safety
Finished <<< drone_interfaces [0.50s]
Starting >>> drone_fc_bridge
100% tests passed, 0 tests failed out of 4
Finished <<< drone_basics_cpp [2.61s]
Starting >>> drone_mission
======================== 13 passed, 1 skipped in 9.63s =========================
======================== 47 passed, 1 skipped in 7.96s =========================
================== 28 passed, 1 skipped, 4 warnings in 10.66s ==================
Finished <<< drone_safety [11.9s]
Finished <<< drone_mission [10.1s]
Finished <<< drone_basics_py [12.9s]
100% tests passed, 0 tests failed out of 4
Finished <<< drone_fc_bridge [40.5s]
Starting >>> drone_bringup
100% tests passed, 0 tests failed out of 4
Finished <<< drone_bringup [1.36s]
Summary: 7 packages finished [42.6s]
Summary: 135 tests, 0 errors, 0 failures, 4 skipped
```

`colcon test-result --verbose`, the last step of the CI workflow:

```text
Summary: 135 tests, 0 errors, 0 failures, 4 skipped
```

The full console log (1098 lines) is in `test_report_console.log` next to this file.
