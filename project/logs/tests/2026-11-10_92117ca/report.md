# Test run 2026-11-10_92117ca: PASSED

- **When:** 2026-11-10T12:44:43+00:00, on joao-barros-Vostro-5568
- **Code:** `92117ca` on `staging`: Merge main into staging: INAV-4 inventory and captures, real_flow, lint fix
- **Environment:** ROS jazzy, Ubuntu 24.04.5 LTS, Python 3.12.3, dev container; clean build, the same commands as CI
- **Build:** exit 0, 46 s. **Tests:** exit 0, 43 s

## Result

| | Test cases | Passed | Skipped | Failed |
| --- | --- | --- | --- | --- |
| Behaviour tests | 110 | 110 | 0 | 0 |
| Lint and style checks | 27 | 22 | 5 | 0 |
| **Total** | 137 | 132 | 5 | 0 |

colcon's own summary counts 149 "tests": the 137 test cases plus 12 CTest entries (one per C++ test file or linter), which wrap cases already counted.

## Compared with the previous run

Previous: `2026-11-05_ab8985a-dirty` (`ab8985a`): 123 cases, 0 failed. Now: 137 cases, 0 failed.

**New tests:**
- `drone_sim_sensors` `test_copyright` `test_copyright`: skipped
- `drone_sim_sensors` `test_flake8` `test_flake8`: passed
- `drone_sim_sensors` `test_flow_model` `test_forward_gives_negative_flow_y`: passed
- `drone_sim_sensors` `test_flow_model` `test_hover_gives_no_flow`: passed
- `drone_sim_sensors` `test_flow_model` `test_left_gives_positive_flow_x`: passed
- `drone_sim_sensors` `test_flow_model` `test_measure_passes_ideal_flow_when_clean`: passed
- `drone_sim_sensors` `test_flow_model` `test_measure_too_fast_has_no_quality`: passed
- `drone_sim_sensors` `test_flow_model` `test_measure_too_low_has_no_quality`: passed
- `drone_sim_sensors` `test_flow_model` `test_noise_has_the_requested_spread`: passed
- `drone_sim_sensors` `test_flow_model` `test_rotation_in_place_equals_body_rate`: passed
- `drone_sim_sensors` `test_flow_model` `test_tilt_lengthens_the_distance`: passed
- `drone_sim_sensors` `test_flow_model` `test_unusable_geometry_gives_none`: passed
- `drone_sim_sensors` `test_flow_model` `test_whole_degrees_truncate_toward_zero`: passed
- `drone_sim_sensors` `test_pep257` `test_pep257`: passed

## By package

| Package | Behaviour | Lint | Passed | Skipped | Failed | Time |
| --- | --- | --- | --- | --- | --- | --- |
| `drone_basics_cpp` | 0 | 4 | 3 | 1 | 0 | 2.95 s |
| `drone_basics_py` | 24 | 5 | 28 | 1 | 0 | 13.2 s |
| `drone_bringup` | 0 | 5 | 5 | 0 | 0 | 1.45 s |
| `drone_fc_bridge` | 23 | 0 | 23 | 0 | 0 | 40.5 s |
| `drone_mission` | 43 | 5 | 47 | 1 | 0 | 12.3 s |
| `drone_safety` | 9 | 5 | 13 | 1 | 0 | 11.8 s |
| `drone_sim_sensors` | 11 | 3 | 13 | 1 | 0 | 1.90 s |

## Every test

### `drone_basics_cpp` · `cppcheck` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `src/watchdog.cpp` | skipped | 0.000 | Test Skipped due to cppcheck 2.13.0 performance issues |

### `drone_basics_cpp` · `lint_cmake` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `CMakeLists.txt` | pass | 0.000 |  |

### `drone_basics_cpp` · `uncrustify` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `src/watchdog.cpp` | pass | 0.000 |  |

### `drone_basics_cpp` · `xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `package.xml` | pass | 0.000 |  |

### `drone_basics_py` · `test_copyright` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_copyright` | skipped | 0.001 | No copyright header has been placed in the generated source file. |

### `drone_basics_py` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.327 |  |

### `drone_basics_py` · `test_mypy` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mypy` | pass | 8.611 |  |

### `drone_basics_py` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.069 |  |

### `drone_basics_py` · `test_radio_teleop` (24)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_switch_off_publishes_nothing` | pass | 0.129 |  |
| `test_engage_after_hold` | pass | 0.083 |  |
| `test_no_engage_before_hold` | pass | 0.016 |  |
| `test_bounce_while_arming_does_not_engage` | pass | 0.016 |  |
| `test_engages_once_bounce_settles` | pass | 0.020 |  |
| `test_off_is_immediate` | pass | 0.025 |  |
| `test_bounce_while_disarming_does_not_reengage` | pass | 0.035 |  |
| `test_engage_refused_with_throttle_off_centre` | pass | 0.022 |  |
| `test_throttle_moves_freely_once_engaged` | pass | 0.022 |  |
| `test_sticks_scaled_to_limits` | pass | 0.021 |  |
| `test_deadband_gives_zero` | pass | 0.021 |  |
| `test_reengage_needs_throttle_centred_again` | pass | 0.030 |  |
| `test_switch_at_threshold_is_off` | pass | 0.020 |  |
| `test_missing_arm_axis_is_off` | pass | 0.020 |  |
| `test_arm_switch_arms_the_fc_once` | pass | 0.021 |  |
| `test_arm_switch_off_disarms_even_in_flight` | pass | 0.020 |  |
| `test_arm_switch_on_at_start_must_be_cycled` | pass | 0.020 |  |
| `test_arming_refused_with_throttle_off_centre` | pass | 0.022 |  |
| `test_arm_alone_does_not_take_over` | pass | 0.016 |  |
| `test_takeover_alone_does_nothing` | pass | 0.020 |  |
| `test_takeover_with_arm_on_engages_after_hold` | pass | 0.027 |  |
| `test_takeover_off_releases_at_once` | pass | 0.025 |  |
| `test_arm_off_releases_even_with_takeover_on` | pass | 0.033 |  |
| `test_missing_takeover_axis_is_off` | pass | 0.027 |  |

### `drone_basics_py` · `test_xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_xmllint` | pass | 0.315 |  |

### `drone_bringup` · `flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `flake8` | pass | 0.000 |  |

### `drone_bringup` · `lint_cmake` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `CMakeLists.txt` | pass | 0.000 |  |

### `drone_bringup` · `pep257` (2)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `./launch/basics.launch.py` | pass | 0.000 |  |
| `./launch/sim.launch.py` | pass | 0.000 |  |

### `drone_bringup` · `xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `package.xml` | pass | 0.000 |  |

### `drone_fc_bridge` · `test_failsafes` (9)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_fresh_setpoint_is_forwarded` | pass | 1.807 |  |
| `test_horizontal_clamp_keeps_direction` | pass | 1.809 |  |
| `test_inf_is_rejected` | pass | 1.809 |  |
| `test_nan_is_rejected_and_times_out` | pass | 2.311 |  |
| `test_roll_and_pitch_rates_are_zeroed` | pass | 1.809 |  |
| `test_sim_enable_is_published` | pass | 2.313 |  |
| `test_timeout_sends_zero` | pass | 2.810 |  |
| `test_vertical_and_yaw_clamp` | pass | 2.818 |  |
| `test_zero_without_setpoints` | pass | 1.810 |  |

### `drone_fc_bridge` · `test_inav` (3)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_arm_is_refused` | pass | 0.008 |  |
| `test_nothing_reaches_the_sim` | pass | 0.000 |  |
| `test_status_says_inav_and_disarmed` | pass | 0.000 |  |

### `drone_fc_bridge` · `test_services` (4)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_disarm_and_rearm` | pass | 3.020 |  |
| `test_hold_sends_zero_despite_setpoints` | pass | 1.537 |  |
| `test_starts_armed` | pass | 0.000 |  |
| `test_status_reports_setpoint_age` | pass | 1.441 |  |

### `drone_fc_bridge` · `test_state` (7)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_body_velocity_rotated_by_heading` | pass | 1.534 |  |
| `test_height_and_orientation_from_sim` | pass | 0.415 |  |
| `test_position_is_integrated_not_copied` | pass | 1.528 |  |
| `test_range_level` | pass | 0.415 |  |
| `test_range_out_of_range_is_inf` | pass | 1.241 |  |
| `test_range_reads_longer_when_tilted` | pass | 0.408 |  |
| `test_velocity_passes_through` | pass | 0.614 |  |

### `drone_mission` · `test_copyright` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_copyright` | skipped | 0.001 | No copyright header has been placed in the generated source file. |

### `drone_mission` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.640 |  |

### `drone_mission` · `test_logic` (43)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_starts_grounded_and_silent` | pass | 0.001 |  |
| `test_takeoff_hold_land` | pass | 0.003 |  |
| `test_takeoff_to_a_given_height` | pass | 0.002 |  |
| `test_takeoff_refused_without_range` | pass | 0.002 |  |
| `test_takeoff_refused_above_range_max` | pass | 0.001 |  |
| `test_takeoff_refused_in_the_air` | pass | 0.002 |  |
| `test_takeoff_timeout_lands` | pass | 0.003 |  |
| `test_cancel_takeoff_holds_where_it_is` | pass | 0.001 |  |
| `test_goto_forward` | pass | 0.005 |  |
| `test_goto_is_relative_to_heading` | pass | 0.007 |  |
| `test_goto_square_comes_back` | pass | 0.012 |  |
| `test_goto_refused_on_the_ground_and_during_takeoff` | pass | 0.001 |  |
| `test_goto_refused_without_odometry` | pass | 0.002 |  |
| `test_goto_aborts_when_odometry_stops` | pass | 0.002 |  |
| `test_goto_timeout` | pass | 0.004 |  |
| `test_cancel_goto_holds` | pass | 0.002 |  |
| `test_land_preempts_goto` | pass | 0.005 |  |
| `test_land_cannot_be_cancelled` | pass | 0.002 |  |
| `test_land_refused_on_the_ground` | pass | 0.001 |  |
| `test_hold_corrects_sag` | pass | 0.005 |  |
| `test_tilt_correction` | pass | 0.001 |  |
| `test_minus_inf_is_the_ground` | pass | 0.001 |  |
| `test_range_lost_hovers_then_resumes_hold` | pass | 0.002 |  |
| `test_range_lost_aborts_goto` | pass | 0.002 |  |
| `test_range_lost_too_long_lands_blind` | pass | 0.003 |  |
| `test_land_goal_during_autonomous_landing` | pass | 0.003 |  |
| `test_goto_feedback` | pass | 0.002 |  |
| `test_takeoff_refused_until_range_is_steady` | pass | 0.003 |  |
| `test_range_gap_restarts_the_steady_time` | pass | 0.002 |  |
| `test_range_lost_on_the_ground_during_takeoff_stays_grounded` | pass | 0.002 |  |
| `test_range_lost_mid_takeoff_holds_the_height_reached` | pass | 0.002 |  |
| `test_override_aborts_the_goal_and_goes_quiet` | pass | 0.003 |  |
| `test_goals_refused_while_overridden` | pass | 0.001 |  |
| `test_control_back_in_the_air_holds_where_it_is` | pass | 0.005 |  |
| `test_control_back_on_the_ground_stays_grounded` | pass | 0.003 |  |
| `test_override_during_land_aborts_it` | pass | 0.002 |  |
| `test_repeated_control_messages_change_nothing` | pass | 0.002 |  |
| `test_takeoff_refused_until_armed` | pass | 0.001 |  |
| `test_takeoff_refused_before_any_status` | pass | 0.002 |  |
| `test_without_radio_arming_takeoff_needs_no_arm` | pass | 0.001 |  |
| `test_stale_disarmed_status_does_not_abort_takeoff` | pass | 0.002 |  |
| `test_disarm_in_the_air_aborts_and_goes_quiet` | pass | 0.002 |  |
| `test_disarm_on_the_ground_changes_nothing` | pass | 0.001 |  |

### `drone_mission` · `test_mypy` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mypy` | pass | 9.107 |  |

### `drone_mission` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.095 |  |

### `drone_mission` · `test_xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_xmllint` | pass | 0.312 |  |

### `drone_safety` · `test_arbiter` (9)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_nothing_active_at_start` | pass | 0.001 |  |
| `test_single_source_is_forwarded` | pass | 0.001 |  |
| `test_radio_takes_over_from_mission` | pass | 0.001 |  |
| `test_manual_beats_mission_but_not_radio` | pass | 0.001 |  |
| `test_control_returns_when_the_radio_goes_quiet` | pass | 0.001 |  |
| `test_everything_quiet_is_none` | pass | 0.001 |  |
| `test_unknown_source_is_never_forwarded` | pass | 0.001 |  |
| `test_update_reports_changes_once` | pass | 0.001 |  |
| `test_time_going_backwards_is_not_fresh` | pass | 0.001 |  |

### `drone_safety` · `test_copyright` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_copyright` | skipped | 0.000 | No copyright header has been placed in the generated source file. |

### `drone_safety` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.397 |  |

### `drone_safety` · `test_mypy` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mypy` | pass | 8.633 |  |

### `drone_safety` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.054 |  |

### `drone_safety` · `test_xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_xmllint` | pass | 0.317 |  |

### `drone_sim_sensors` · `test_copyright` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_copyright` | skipped | 0.000 | No copyright header has been placed in the generated source file. |

### `drone_sim_sensors` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.173 |  |

### `drone_sim_sensors` · `test_flow_model` (11)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_hover_gives_no_flow` | pass | 0.001 |  |
| `test_forward_gives_negative_flow_y` | pass | 0.001 |  |
| `test_left_gives_positive_flow_x` | pass | 0.001 |  |
| `test_rotation_in_place_equals_body_rate` | pass | 0.001 |  |
| `test_tilt_lengthens_the_distance` | pass | 0.001 |  |
| `test_unusable_geometry_gives_none` | pass | 0.001 |  |
| `test_whole_degrees_truncate_toward_zero` | pass | 0.001 |  |
| `test_measure_passes_ideal_flow_when_clean` | pass | 0.001 |  |
| `test_measure_too_low_has_no_quality` | pass | 0.001 |  |
| `test_measure_too_fast_has_no_quality` | pass | 0.001 |  |
| `test_noise_has_the_requested_spread` | pass | 0.010 |  |

### `drone_sim_sensors` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.040 |  |

## Warnings in the output

Lines mentioning a warning (node log lines at WARN level left out: those are the behaviour under test):

```text
Warning: This process (pid=1257) is multi-threaded, use of fork() may lead to deadlocks in the child.
Warning: This process (pid=1621) is multi-threaded, use of fork() may lead to deadlocks in the child.
```

## Console summary lines

Packages are tested in parallel, so these lines interleave.

```text
Finished <<< drone_interfaces [0.55s]
100% tests passed, 0 tests failed out of 4
Finished <<< drone_basics_cpp [2.95s]
======================== 13 passed, 1 skipped in 9.61s =========================
Finished <<< drone_safety [11.8s]
================== 28 passed, 1 skipped, 4 warnings in 10.95s ==================
Finished <<< drone_basics_py [13.2s]
================== 13 passed, 1 skipped, 4 warnings in 0.73s ===================
Finished <<< drone_sim_sensors [1.90s]
======================== 47 passed, 1 skipped in 10.52s ========================
Finished <<< drone_mission [12.3s]
100% tests passed, 0 tests failed out of 4
Finished <<< drone_fc_bridge [40.5s]
100% tests passed, 0 tests failed out of 4
Finished <<< drone_bringup [1.45s]
Summary: 8 packages finished [42.8s]
Summary: 149 tests, 0 errors, 0 failures, 5 skipped
```

Full output: `console.log.gz` (`zcat console.log.gz | less`). Every test case, with any failure message: `results.json`.
