# Test run 2026-11-10_70cdf3d: PASSED

- **When:** 2026-11-10T16:17:48+00:00, on joao-barros-Vostro-5568
- **Code:** `70cdf3d` on `staging`: ROS-6 step A: MSP v2 framing and INAV decoders for fc_bridge (#135)
- **Environment:** ROS jazzy, Ubuntu 24.04.5 LTS, Python 3.12.3, dev container; clean build, the same commands as CI
- **Build:** exit 0, 45 s. **Tests:** exit 0, 43 s

## Result

| | Test cases | Passed | Skipped | Failed |
| --- | --- | --- | --- | --- |
| Behaviour tests | 147 | 147 | 0 | 0 |
| Lint and style checks | 27 | 22 | 5 | 0 |
| **Total** | 174 | 169 | 5 | 0 |

colcon's own summary counts 188 "tests": the 174 test cases plus 14 CTest entries (one per C++ test file or linter), which wrap cases already counted.

## Compared with the previous run

Previous: `2026-11-10_92117ca` (`92117ca`): 137 cases, 0 failed. Now: 174 cases, 0 failed.

**New tests:**
- `drone_fc_bridge` `test_inav_decode` `Analog`: passed
- `drone_fc_bridge` `test_inav_decode` `AnalogHandBuilt`: passed
- `drone_fc_bridge` `test_inav_decode` `ApiVersion`: passed
- `drone_fc_bridge` `test_inav_decode` `Attitude`: passed
- `drone_fc_bridge` `test_inav_decode` `AttitudeLimits`: passed
- `drone_fc_bridge` `test_inav_decode` `FcVariant`: passed
- `drone_fc_bridge` `test_inav_decode` `FcVersion`: passed
- `drone_fc_bridge` `test_inav_decode` `LocalPose`: passed
- `drone_fc_bridge` `test_inav_decode` `LocalPoseHandBuilt`: passed
- `drone_fc_bridge` `test_inav_decode` `OpticalFlow`: passed
- `drone_fc_bridge` `test_inav_decode` `OpticalFlowHandBuilt`: passed
- `drone_fc_bridge` `test_inav_decode` `RangefinderFromCaptures`: passed
- `drone_fc_bridge` `test_inav_decode` `RangefinderStates`: passed
- `drone_fc_bridge` `test_inav_decode` `Status`: passed
- `drone_fc_bridge` `test_inav_decode` `StatusHandBuilt`: passed
- `drone_fc_bridge` `test_inav_decode` `StatusInEveryCapture`: passed
- `drone_fc_bridge` `test_msp` `BufferStaysBoundedOnGarbage`: passed
- `drone_fc_bridge` `test_msp` `DamagedFramesAreNotReturned`: passed
- `drone_fc_bridge` `test_msp` `DrainsABigBacklogInLinearTime`: passed
- `drone_fc_bridge` `test_msp` `ErrorFrame`: passed
- `drone_fc_bridge` `test_msp` `EveryGoodFrameParses`: passed
- `drone_fc_bridge` `test_msp` `FeedAfterPartialDrainKeepsOrder`: passed
- `drone_fc_bridge` `test_msp` `FrameSplitAtEveryPoint`: passed
- `drone_fc_bridge` `test_msp` `IgnoresRequestFrames`: passed
- `drone_fc_bridge` `test_msp` `LargestPayloadIsAccepted`: passed
- `drone_fc_bridge` `test_msp` `MatchesCapturedFrames`: passed
- `drone_fc_bridge` `test_msp` `OnlyReadCommands`: passed
- `drone_fc_bridge` `test_msp` `OversizedSizeDoesNotStall`: passed
- `drone_fc_bridge` `test_msp` `PayloadAndItsLimit`: passed
- `drone_fc_bridge` `test_msp` `RecoversFrameEmbeddedInDamagedOne`: passed
- `drone_fc_bridge` `test_msp` `RejectsBadCrc`: passed
- `drone_fc_bridge` `test_msp` `ResetDropsHalfFrame`: passed
- `drone_fc_bridge` `test_msp` `SameBytesAsPython`: passed
- `drone_fc_bridge` `test_msp` `SkipPendingReleasesTheRepliesBehindIt`: passed
- `drone_fc_bridge` `test_msp` `SkipsGarbageBetweenFrames`: passed
- `drone_fc_bridge` `test_msp` `StandardCheckValue`: passed
- `drone_fc_bridge` `test_msp` `WholeFileAsOneStream`: passed

## By package

| Package | Behaviour | Lint | Passed | Skipped | Failed | Time |
| --- | --- | --- | --- | --- | --- | --- |
| `drone_basics_cpp` | 0 | 4 | 3 | 1 | 0 | 2.03 s |
| `drone_basics_py` | 24 | 5 | 28 | 1 | 0 | 13.0 s |
| `drone_bringup` | 0 | 5 | 5 | 0 | 0 | 1.39 s |
| `drone_fc_bridge` | 60 | 0 | 60 | 0 | 0 | 40.9 s |
| `drone_mission` | 43 | 5 | 47 | 1 | 0 | 8.62 s |
| `drone_safety` | 9 | 5 | 13 | 1 | 0 | 11.8 s |
| `drone_sim_sensors` | 11 | 3 | 13 | 1 | 0 | 1.66 s |

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
| `test_copyright` | skipped | 0.000 | No copyright header has been placed in the generated source file. |

### `drone_basics_py` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.315 |  |

### `drone_basics_py` · `test_mypy` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mypy` | pass | 8.670 |  |

### `drone_basics_py` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.065 |  |

### `drone_basics_py` · `test_radio_teleop` (24)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_switch_off_publishes_nothing` | pass | 0.121 |  |
| `test_engage_after_hold` | pass | 0.093 |  |
| `test_no_engage_before_hold` | pass | 0.018 |  |
| `test_bounce_while_arming_does_not_engage` | pass | 0.019 |  |
| `test_engages_once_bounce_settles` | pass | 0.020 |  |
| `test_off_is_immediate` | pass | 0.017 |  |
| `test_bounce_while_disarming_does_not_reengage` | pass | 0.019 |  |
| `test_engage_refused_with_throttle_off_centre` | pass | 0.021 |  |
| `test_throttle_moves_freely_once_engaged` | pass | 0.021 |  |
| `test_sticks_scaled_to_limits` | pass | 0.023 |  |
| `test_deadband_gives_zero` | pass | 0.024 |  |
| `test_reengage_needs_throttle_centred_again` | pass | 0.027 |  |
| `test_switch_at_threshold_is_off` | pass | 0.021 |  |
| `test_missing_arm_axis_is_off` | pass | 0.327 |  |
| `test_arm_switch_arms_the_fc_once` | pass | 0.023 |  |
| `test_arm_switch_off_disarms_even_in_flight` | pass | 0.026 |  |
| `test_arm_switch_on_at_start_must_be_cycled` | pass | 0.025 |  |
| `test_arming_refused_with_throttle_off_centre` | pass | 0.022 |  |
| `test_arm_alone_does_not_take_over` | pass | 0.018 |  |
| `test_takeover_alone_does_nothing` | pass | 0.018 |  |
| `test_takeover_with_arm_on_engages_after_hold` | pass | 0.020 |  |
| `test_takeover_off_releases_at_once` | pass | 0.019 |  |
| `test_arm_off_releases_even_with_takeover_on` | pass | 0.023 |  |
| `test_missing_takeover_axis_is_off` | pass | 0.022 |  |

### `drone_basics_py` · `test_xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_xmllint` | pass | 0.211 |  |

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

### `drone_fc_bridge` · `test_inav_decode` (16)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `ApiVersion` | pass | 0.000 |  |
| `FcVariant` | pass | 0.000 |  |
| `FcVersion` | pass | 0.000 |  |
| `RangefinderFromCaptures` | pass | 0.000 |  |
| `RangefinderStates` | pass | 0.000 |  |
| `Attitude` | pass | 0.000 |  |
| `AttitudeLimits` | pass | 0.000 |  |
| `Status` | pass | 0.000 |  |
| `StatusInEveryCapture` | pass | 0.006 |  |
| `StatusHandBuilt` | pass | 0.000 |  |
| `OpticalFlow` | pass | 0.000 |  |
| `OpticalFlowHandBuilt` | pass | 0.000 |  |
| `Analog` | pass | 0.000 |  |
| `AnalogHandBuilt` | pass | 0.000 |  |
| `LocalPose` | pass | 0.000 |  |
| `LocalPoseHandBuilt` | pass | 0.000 |  |

### `drone_fc_bridge` · `test_msp` (21)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `StandardCheckValue` | pass | 0.000 |  |
| `MatchesCapturedFrames` | pass | 0.000 |  |
| `SameBytesAsPython` | pass | 0.000 |  |
| `OnlyReadCommands` | pass | 0.000 |  |
| `PayloadAndItsLimit` | pass | 0.000 |  |
| `EveryGoodFrameParses` | pass | 0.009 |  |
| `DamagedFramesAreNotReturned` | pass | 0.006 |  |
| `WholeFileAsOneStream` | pass | 0.030 |  |
| `RecoversFrameEmbeddedInDamagedOne` | pass | 0.009 |  |
| `SkipsGarbageBetweenFrames` | pass | 0.000 |  |
| `FrameSplitAtEveryPoint` | pass | 0.000 |  |
| `IgnoresRequestFrames` | pass | 0.000 |  |
| `ErrorFrame` | pass | 0.000 |  |
| `RejectsBadCrc` | pass | 0.000 |  |
| `OversizedSizeDoesNotStall` | pass | 0.000 |  |
| `LargestPayloadIsAccepted` | pass | 0.000 |  |
| `BufferStaysBoundedOnGarbage` | pass | 0.000 |  |
| `ResetDropsHalfFrame` | pass | 0.000 |  |
| `SkipPendingReleasesTheRepliesBehindIt` | pass | 0.002 |  |
| `DrainsABigBacklogInLinearTime` | pass | 0.107 |  |
| `FeedAfterPartialDrainKeepsOrder` | pass | 0.000 |  |

### `drone_fc_bridge` · `test_failsafes` (9)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_fresh_setpoint_is_forwarded` | pass | 1.818 |  |
| `test_horizontal_clamp_keeps_direction` | pass | 1.821 |  |
| `test_inf_is_rejected` | pass | 1.811 |  |
| `test_nan_is_rejected_and_times_out` | pass | 2.329 |  |
| `test_roll_and_pitch_rates_are_zeroed` | pass | 1.811 |  |
| `test_sim_enable_is_published` | pass | 2.312 |  |
| `test_timeout_sends_zero` | pass | 2.818 |  |
| `test_vertical_and_yaw_clamp` | pass | 2.832 |  |
| `test_zero_without_setpoints` | pass | 1.818 |  |

### `drone_fc_bridge` · `test_inav` (3)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_arm_is_refused` | pass | 0.005 |  |
| `test_nothing_reaches_the_sim` | pass | 0.001 |  |
| `test_status_says_inav_and_disarmed` | pass | 0.000 |  |

### `drone_fc_bridge` · `test_services` (4)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_disarm_and_rearm` | pass | 3.021 |  |
| `test_hold_sends_zero_despite_setpoints` | pass | 1.528 |  |
| `test_starts_armed` | pass | 0.000 |  |
| `test_status_reports_setpoint_age` | pass | 1.450 |  |

### `drone_fc_bridge` · `test_state` (7)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_body_velocity_rotated_by_heading` | pass | 1.528 |  |
| `test_height_and_orientation_from_sim` | pass | 0.419 |  |
| `test_position_is_integrated_not_copied` | pass | 1.533 |  |
| `test_range_level` | pass | 0.415 |  |
| `test_range_out_of_range_is_inf` | pass | 1.241 |  |
| `test_range_reads_longer_when_tilted` | pass | 0.418 |  |
| `test_velocity_passes_through` | pass | 0.614 |  |

### `drone_mission` · `test_copyright` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_copyright` | skipped | 0.000 | No copyright header has been placed in the generated source file. |

### `drone_mission` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.380 |  |

### `drone_mission` · `test_logic` (43)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_starts_grounded_and_silent` | pass | 0.001 |  |
| `test_takeoff_hold_land` | pass | 0.002 |  |
| `test_takeoff_to_a_given_height` | pass | 0.002 |  |
| `test_takeoff_refused_without_range` | pass | 0.001 |  |
| `test_takeoff_refused_above_range_max` | pass | 0.001 |  |
| `test_takeoff_refused_in_the_air` | pass | 0.001 |  |
| `test_takeoff_timeout_lands` | pass | 0.002 |  |
| `test_cancel_takeoff_holds_where_it_is` | pass | 0.001 |  |
| `test_goto_forward` | pass | 0.002 |  |
| `test_goto_is_relative_to_heading` | pass | 0.002 |  |
| `test_goto_square_comes_back` | pass | 0.005 |  |
| `test_goto_refused_on_the_ground_and_during_takeoff` | pass | 0.001 |  |
| `test_goto_refused_without_odometry` | pass | 0.001 |  |
| `test_goto_aborts_when_odometry_stops` | pass | 0.001 |  |
| `test_goto_timeout` | pass | 0.002 |  |
| `test_cancel_goto_holds` | pass | 0.001 |  |
| `test_land_preempts_goto` | pass | 0.002 |  |
| `test_land_cannot_be_cancelled` | pass | 0.001 |  |
| `test_land_refused_on_the_ground` | pass | 0.001 |  |
| `test_hold_corrects_sag` | pass | 0.003 |  |
| `test_tilt_correction` | pass | 0.000 |  |
| `test_minus_inf_is_the_ground` | pass | 0.000 |  |
| `test_range_lost_hovers_then_resumes_hold` | pass | 0.001 |  |
| `test_range_lost_aborts_goto` | pass | 0.001 |  |
| `test_range_lost_too_long_lands_blind` | pass | 0.002 |  |
| `test_land_goal_during_autonomous_landing` | pass | 0.002 |  |
| `test_goto_feedback` | pass | 0.001 |  |
| `test_takeoff_refused_until_range_is_steady` | pass | 0.001 |  |
| `test_range_gap_restarts_the_steady_time` | pass | 0.001 |  |
| `test_range_lost_on_the_ground_during_takeoff_stays_grounded` | pass | 0.001 |  |
| `test_range_lost_mid_takeoff_holds_the_height_reached` | pass | 0.001 |  |
| `test_override_aborts_the_goal_and_goes_quiet` | pass | 0.001 |  |
| `test_goals_refused_while_overridden` | pass | 0.001 |  |
| `test_control_back_in_the_air_holds_where_it_is` | pass | 0.002 |  |
| `test_control_back_on_the_ground_stays_grounded` | pass | 0.002 |  |
| `test_override_during_land_aborts_it` | pass | 0.001 |  |
| `test_repeated_control_messages_change_nothing` | pass | 0.001 |  |
| `test_takeoff_refused_until_armed` | pass | 0.001 |  |
| `test_takeoff_refused_before_any_status` | pass | 0.001 |  |
| `test_without_radio_arming_takeoff_needs_no_arm` | pass | 0.001 |  |
| `test_stale_disarmed_status_does_not_abort_takeoff` | pass | 0.001 |  |
| `test_disarm_in_the_air_aborts_and_goes_quiet` | pass | 0.001 |  |
| `test_disarm_on_the_ground_changes_nothing` | pass | 0.001 |  |

### `drone_mission` · `test_mypy` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mypy` | pass | 5.780 |  |

### `drone_mission` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.101 |  |

### `drone_mission` · `test_xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_xmllint` | pass | 0.449 |  |

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
| `test_flake8` | pass | 0.289 |  |

### `drone_safety` · `test_mypy` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mypy` | pass | 8.702 |  |

### `drone_safety` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.033 |  |

### `drone_safety` · `test_xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_xmllint` | pass | 0.456 |  |

### `drone_sim_sensors` · `test_copyright` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_copyright` | skipped | 0.000 | No copyright header has been placed in the generated source file. |

### `drone_sim_sensors` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.184 |  |

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
| `test_measure_too_low_has_no_quality` | pass | 0.000 |  |
| `test_measure_too_fast_has_no_quality` | pass | 0.000 |  |
| `test_noise_has_the_requested_spread` | pass | 0.006 |  |

### `drone_sim_sensors` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.029 |  |

## Warnings in the output

Lines mentioning a warning (node log lines at WARN level left out: those are the behaviour under test):

```text
Warning: This process (pid=34222) is multi-threaded, use of fork() may lead to deadlocks in the child.
Warning: This process (pid=34465) is multi-threaded, use of fork() may lead to deadlocks in the child.
```

## Console summary lines

Packages are tested in parallel, so these lines interleave.

```text
Finished <<< drone_interfaces [0.50s]
100% tests passed, 0 tests failed out of 4
Finished <<< drone_basics_cpp [2.03s]
======================== 47 passed, 1 skipped in 6.91s =========================
Finished <<< drone_mission [8.62s]
======================== 13 passed, 1 skipped in 9.67s =========================
================== 28 passed, 1 skipped, 4 warnings in 11.09s ==================
Finished <<< drone_safety [11.8s]
================== 13 passed, 1 skipped, 4 warnings in 0.73s ===================
Finished <<< drone_sim_sensors [1.66s]
Finished <<< drone_basics_py [13.0s]
100% tests passed, 0 tests failed out of 6
Finished <<< drone_fc_bridge [40.9s]
100% tests passed, 0 tests failed out of 4
Finished <<< drone_bringup [1.39s]
Summary: 8 packages finished [43.0s]
Summary: 188 tests, 0 errors, 0 failures, 5 skipped
```

Full output: `console.log.gz` (`zcat console.log.gz | less`). Every test case, with any failure message: `results.json`.
