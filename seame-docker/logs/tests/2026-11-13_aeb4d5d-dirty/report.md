# Test run 2026-11-13_aeb4d5d-dirty: PASSED

- **When:** 2026-11-13T15:14:23+00:00, on seame-10
- **Code:** `aeb4d5d` on `HEAD`: Merge 7325660cbe3725fbac493b33a38ecb30ca05c93d into e36681e6e9d6c0df06521a3626022977d7db0f45
- **Uncommitted code changes were part of this run** (3 file(s)), so the commit alone does not say what ran: `seame-docker/ros2_ws/src/drone_bringup/test/fake_drone.py`, `seame-docker/ros2_ws/src/drone_bringup/test/test_launch_files.py`, `seame-docker/ros2_ws/src/drone_bringup/test/test_stack.py`
- Other uncommitted files (not code, don't affect the tests): `seame-docker/logs/tests/history.csv`, `seame-docker/logs/tests/2026-11-12_d7245d1/console.log.gz`, `seame-docker/logs/tests/2026-11-12_d7245d1/meta.json`, `seame-docker/logs/tests/2026-11-12_d7245d1/report.md`, `seame-docker/logs/tests/2026-11-12_d7245d1/results.json`, `seame-docker/logs/tests/2026-11-13_32cfee3/console.log.gz`, `seame-docker/logs/tests/2026-11-13_32cfee3/meta.json`, `seame-docker/logs/tests/2026-11-13_32cfee3/report.md`, `seame-docker/logs/tests/2026-11-13_32cfee3/results.json`, `seame-docker/logs/tests/2026-11-13_f51dc22-dirty/console.log.gz`, `seame-docker/logs/tests/2026-11-13_f51dc22-dirty/meta.json`, `seame-docker/logs/tests/2026-11-13_f51dc22-dirty/report.md`, `seame-docker/logs/tests/2026-11-13_f51dc22-dirty/results.json`, `seame-docker/logs/tests/2026-11-13_f51dc22/console.log.gz`, `seame-docker/logs/tests/2026-11-13_f51dc22/meta.json`, `seame-docker/logs/tests/2026-11-13_f51dc22/report.md`, `seame-docker/logs/tests/2026-11-13_f51dc22/results.json`
- **Environment:** ROS jazzy, Ubuntu 24.04.5 LTS, Python 3.12.3, dev container; clean build, the same commands as CI
- **Build:** exit 0, 21 s. **Tests:** exit 0, 106 s

## Result

| | Test cases | Passed | Skipped | Failed |
| --- | --- | --- | --- | --- |
| Behaviour tests | 226 | 226 | 0 | 0 |
| Lint and style checks | 33 | 28 | 5 | 0 |
| **Total** | 259 | 254 | 5 | 0 |

colcon's own summary counts 277 "tests": the 259 test cases plus 18 CTest entries (one per C++ test file or linter), which wrap cases already counted.

## Compared with the previous run

Previous: `2026-11-13_32cfee3` (`32cfee3`): 259 cases, 4 failed. Now: 259 cases, 0 failed.

**Status changed:**
- `drone_bringup` `test_launch_files` `test_default_is_the_sim_with_the_radio_and_the_mission`: failure → passed
- `drone_bringup` `test_stack` `test_disarm_mid_flight`: failure → passed
- `drone_bringup` `test_stack` `test_full_flight`: failure → passed
- `drone_bringup` `test_stack` `test_radio_takes_over_and_gives_back`: failure → passed

## By package

| Package | Behaviour | Lint | Passed | Skipped | Failed | Time |
| --- | --- | --- | --- | --- | --- | --- |
| `drone_basics_cpp` | 0 | 4 | 3 | 1 | 0 | 1.52 s |
| `drone_basics_py` | 24 | 5 | 28 | 1 | 0 | 5.42 s |
| `drone_bringup` | 67 | 11 | 78 | 0 | 0 | ? s |
| `drone_fc_bridge` | 60 | 0 | 60 | 0 | 0 | 38.6 s |
| `drone_mission` | 44 | 5 | 48 | 1 | 0 | 5.16 s |
| `drone_safety` | 9 | 5 | 13 | 1 | 0 | 4.77 s |
| `drone_sim_sensors` | 22 | 3 | 24 | 1 | 0 | 0.97 s |

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
| `test_flake8` | pass | 0.157 |  |

### `drone_basics_py` · `test_mypy` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mypy` | pass | 2.925 |  |

### `drone_basics_py` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.032 |  |

### `drone_basics_py` · `test_radio_teleop` (24)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_switch_off_publishes_nothing` | pass | 0.065 |  |
| `test_engage_after_hold` | pass | 0.032 |  |
| `test_no_engage_before_hold` | pass | 0.006 |  |
| `test_bounce_while_arming_does_not_engage` | pass | 0.006 |  |
| `test_engages_once_bounce_settles` | pass | 0.006 |  |
| `test_off_is_immediate` | pass | 0.007 |  |
| `test_bounce_while_disarming_does_not_reengage` | pass | 0.007 |  |
| `test_engage_refused_with_throttle_off_centre` | pass | 0.006 |  |
| `test_throttle_moves_freely_once_engaged` | pass | 0.006 |  |
| `test_sticks_scaled_to_limits` | pass | 0.006 |  |
| `test_deadband_gives_zero` | pass | 0.006 |  |
| `test_reengage_needs_throttle_centred_again` | pass | 0.008 |  |
| `test_switch_at_threshold_is_off` | pass | 0.006 |  |
| `test_missing_arm_axis_is_off` | pass | 0.006 |  |
| `test_arm_switch_arms_the_fc_once` | pass | 0.007 |  |
| `test_arm_switch_off_disarms_even_in_flight` | pass | 0.007 |  |
| `test_arm_switch_on_at_start_must_be_cycled` | pass | 0.007 |  |
| `test_arming_refused_with_throttle_off_centre` | pass | 0.007 |  |
| `test_arm_alone_does_not_take_over` | pass | 0.007 |  |
| `test_takeover_alone_does_nothing` | pass | 0.006 |  |
| `test_takeover_with_arm_on_engages_after_hold` | pass | 0.006 |  |
| `test_takeover_off_releases_at_once` | pass | 0.007 |  |
| `test_arm_off_releases_even_with_takeover_on` | pass | 0.008 |  |
| `test_missing_takeover_axis_is_off` | pass | 0.008 |  |

### `drone_basics_py` · `test_xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_xmllint` | pass | 0.294 |  |

### `drone_bringup` · `flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `flake8` | pass | 0.000 |  |

### `drone_bringup` · `lint_cmake` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `CMakeLists.txt` | pass | 0.000 |  |

### `drone_bringup` · `pep257` (8)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `./launch/basics.launch.py` | pass | 0.000 |  |
| `./launch/sim.launch.py` | pass | 0.000 |  |
| `./test/fake_drone.py` | pass | 0.000 |  |
| `./test/test_config.py` | pass | 0.000 |  |
| `./test/test_launch_files.py` | pass | 0.000 |  |
| `./test/test_sim_flight.py` | pass | 0.000 |  |
| `./test/test_stack.py` | pass | 0.000 |  |
| `./test/test_worlds.py` | pass | 0.000 |  |

### `drone_bringup` · `test_config` (17)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mission_climb_speed_equals_fc_limit` | pass | 0.004 |  |
| `test_safety_timeout_equals_fc_timeout` | pass | 0.000 |  |
| `test_command_within_fc_limit[mission-speed-max_speed_xy]` | pass | 0.000 |  |
| `test_command_within_fc_limit[mission-land_speed-max_speed_z]` | pass | 0.000 |  |
| `test_command_within_fc_limit[mission-yaw_rate-max_yaw_rate]` | pass | 0.000 |  |
| `test_command_within_fc_limit[setpoint_pub-speed-max_speed_xy]` | pass | 0.000 |  |
| `test_command_within_fc_limit[setpoint_pub-climb_speed-max_speed_z]` | pass | 0.000 |  |
| `test_command_within_fc_limit[radio_teleop-max_xy-max_speed_xy]` | pass | 0.000 |  |
| `test_command_within_fc_limit[radio_teleop-max_z-max_speed_z]` | pass | 0.000 |  |
| `test_command_within_fc_limit[radio_teleop-max_yaw-max_yaw_rate]` | pass | 0.000 |  |
| `test_heights_inside_rangefinder` | pass | 0.000 |  |
| `test_demo_height_inside_rangefinder` | pass | 0.000 |  |
| `test_flow_works_once_airborne` | pass | 0.000 |  |
| `test_radio_has_top_priority` | pass | 0.000 |  |
| `test_times_and_rates_positive` | pass | 0.000 |  |
| `test_decimals_are_floats` | pass | 0.000 |  |
| `test_every_section_is_a_launched_node` | pass | 0.000 |  |

### `drone_bringup` · `test_launch_files` (24)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_default_is_the_sim_with_the_radio_and_the_mission` | pass | 0.014 |  |
| `test_inav_backend_starts_no_gazebo_and_no_radio_nodes` | pass | 0.002 |  |
| `test_with_the_radio_only_the_radio_arms` | pass | 0.005 |  |
| `test_without_the_radio_the_mission_arms` | pass | 0.003 |  |
| `test_demo_flight_only_with_demo` | pass | 0.007 |  |
| `test_circle_demo_starts_setpoint_pub_after_the_rest` | pass | 0.004 |  |
| `test_nothing_flies_without_a_source[source:=circle demo:=false]` | pass | 0.003 |  |
| `test_nothing_flies_without_a_source[source:=none demo:=false]` | pass | 0.003 |  |
| `test_nothing_flies_without_a_source[source:=none demo:=true]` | pass | 0.003 |  |
| `test_gazebo_gets_the_world_and_headless_adds_server_only` | pass | 0.007 |  |
| `test_each_source_publishes_on_its_own_topic` | pass | 0.007 |  |
| `test_sim_time_only_in_the_sim` | pass | 0.108 |  |
| `test_every_node_reads_sim_yaml` | pass | 0.100 |  |
| `test_our_programs_are_installed` | pass | 0.099 |  |
| `test_other_programs_are_installed` | pass | 0.099 |  |
| `test_parameter_files_are_installed` | pass | 0.099 |  |
| `test_every_package_it_starts_is_a_dependency` | pass | 0.099 |  |
| `test_every_package_it_starts_is_checked_first` | pass | 0.099 |  |
| `test_a_missing_package_stops_the_launch[drone_mission]` | pass | 0.001 |  |
| `test_a_missing_package_stops_the_launch[drone_fc_bridge]` | pass | 0.001 |  |
| `test_a_missing_package_stops_the_launch[ros_gz_bridge]` | pass | 0.001 |  |
| `test_a_missing_package_stops_the_launch[joy]` | pass | 0.001 |  |
| `test_the_real_drone_needs_none_of_the_sim_packages` | pass | 0.002 |  |
| `test_refuses_to_start_next_to_a_running_sim` | pass | 0.002 |  |

### `drone_bringup` · `test_stack` (5)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_disarm_mid_flight` | pass | 8.803 |  |
| `test_disarm_while_the_radio_flies` | pass | 7.861 |  |
| `test_full_flight` | pass | 26.975 |  |
| `test_radio_takes_over_and_gives_back` | pass | 18.299 |  |
| `test_takeoff_refused_until_armed` | pass | 1.223 |  |

### `drone_bringup` · `test_worlds` (21)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_bridge_talks_to_one_drone` | pass | 0.002 |  |
| `test_world_loads_physics[outdoor_field.sdf]` | pass | 0.002 |  |
| `test_world_loads_physics[room_world.sdf]` | pass | 0.000 |  |
| `test_world_loads_physics[multicopter_velocity_control.sdf]` | pass | 0.000 |  |
| `test_drone_takes_our_commands[outdoor_field.sdf]` | pass | 0.002 |  |
| `test_drone_takes_our_commands[room_world.sdf]` | pass | 0.000 |  |
| `test_drone_takes_our_commands[multicopter_velocity_control.sdf]` | pass | 0.000 |  |
| `test_drone_publishes_the_odometry_we_read[outdoor_field.sdf]` | pass | 0.002 |  |
| `test_drone_publishes_the_odometry_we_read[room_world.sdf]` | pass | 0.000 |  |
| `test_drone_publishes_the_odometry_we_read[multicopter_velocity_control.sdf]` | pass | 0.000 |  |
| `test_drone_starts_on_the_ground[outdoor_field.sdf]` | pass | 0.002 |  |
| `test_drone_starts_on_the_ground[room_world.sdf]` | pass | 0.000 |  |
| `test_drone_starts_on_the_ground[multicopter_velocity_control.sdf]` | pass | 0.000 |  |
| `test_drone_fuel_model_is_pinned[outdoor_field.sdf]` | pass | 0.002 |  |
| `test_drone_fuel_model_is_pinned[room_world.sdf]` | pass | 0.000 |  |
| `test_drone_fuel_model_is_pinned[multicopter_velocity_control.sdf]` | pass | 0.000 |  |
| `test_models_it_uses_exist[outdoor_field.sdf]` | pass | 0.002 |  |
| `test_models_it_uses_exist[room_world.sdf]` | pass | 0.000 |  |
| `test_models_it_uses_exist[multicopter_velocity_control.sdf]` | pass | 0.000 |  |
| `test_every_model_has_its_files` | pass | 0.002 |  |
| `test_worlds_and_models_are_installed` | pass | 0.000 |  |

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
| `StatusInEveryCapture` | pass | 0.004 |  |
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
| `EveryGoodFrameParses` | pass | 0.008 |  |
| `DamagedFramesAreNotReturned` | pass | 0.005 |  |
| `WholeFileAsOneStream` | pass | 0.019 |  |
| `RecoversFrameEmbeddedInDamagedOne` | pass | 0.007 |  |
| `SkipsGarbageBetweenFrames` | pass | 0.000 |  |
| `FrameSplitAtEveryPoint` | pass | 0.000 |  |
| `IgnoresRequestFrames` | pass | 0.000 |  |
| `ErrorFrame` | pass | 0.000 |  |
| `RejectsBadCrc` | pass | 0.000 |  |
| `OversizedSizeDoesNotStall` | pass | 0.000 |  |
| `LargestPayloadIsAccepted` | pass | 0.000 |  |
| `BufferStaysBoundedOnGarbage` | pass | 0.000 |  |
| `ResetDropsHalfFrame` | pass | 0.000 |  |
| `SkipPendingReleasesTheRepliesBehindIt` | pass | 0.001 |  |
| `DrainsABigBacklogInLinearTime` | pass | 0.060 |  |
| `FeedAfterPartialDrainKeepsOrder` | pass | 0.000 |  |

### `drone_fc_bridge` · `test_failsafes` (9)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_fresh_setpoint_is_forwarded` | pass | 1.808 |  |
| `test_horizontal_clamp_keeps_direction` | pass | 1.810 |  |
| `test_inf_is_rejected` | pass | 1.811 |  |
| `test_nan_is_rejected_and_times_out` | pass | 2.319 |  |
| `test_roll_and_pitch_rates_are_zeroed` | pass | 1.821 |  |
| `test_sim_enable_is_published` | pass | 2.311 |  |
| `test_timeout_sends_zero` | pass | 2.808 |  |
| `test_vertical_and_yaw_clamp` | pass | 2.831 |  |
| `test_zero_without_setpoints` | pass | 1.811 |  |

### `drone_fc_bridge` · `test_inav` (3)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_arm_is_refused` | pass | 0.003 |  |
| `test_nothing_reaches_the_sim` | pass | 0.000 |  |
| `test_status_says_inav_and_disarmed` | pass | 0.000 |  |

### `drone_fc_bridge` · `test_services` (4)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_disarm_and_rearm` | pass | 3.020 |  |
| `test_hold_sends_zero_despite_setpoints` | pass | 1.520 |  |
| `test_starts_armed` | pass | 0.000 |  |
| `test_status_reports_setpoint_age` | pass | 1.459 |  |

### `drone_fc_bridge` · `test_state` (7)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_body_velocity_rotated_by_heading` | pass | 1.524 |  |
| `test_height_and_orientation_from_sim` | pass | 0.409 |  |
| `test_position_is_integrated_not_copied` | pass | 1.521 |  |
| `test_range_level` | pass | 0.410 |  |
| `test_range_out_of_range_is_inf` | pass | 1.220 |  |
| `test_range_reads_longer_when_tilted` | pass | 0.406 |  |
| `test_velocity_passes_through` | pass | 0.610 |  |

### `drone_mission` · `test_copyright` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_copyright` | skipped | 0.000 | No copyright header has been placed in the generated source file. |

### `drone_mission` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.170 |  |

### `drone_mission` · `test_logic` (44)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_starts_grounded_and_silent` | pass | 0.001 |  |
| `test_takeoff_hold_land` | pass | 0.002 |  |
| `test_takeoff_to_a_given_height` | pass | 0.001 |  |
| `test_takeoff_refused_without_range` | pass | 0.001 |  |
| `test_takeoff_refused_above_range_max` | pass | 0.001 |  |
| `test_takeoff_refused_in_the_air` | pass | 0.001 |  |
| `test_takeoff_timeout_lands` | pass | 0.001 |  |
| `test_cancel_takeoff_holds_where_it_is` | pass | 0.001 |  |
| `test_goto_forward` | pass | 0.001 |  |
| `test_goto_is_relative_to_heading` | pass | 0.001 |  |
| `test_goto_square_comes_back` | pass | 0.002 |  |
| `test_goto_refused_on_the_ground_and_during_takeoff` | pass | 0.000 |  |
| `test_goto_refused_without_odometry` | pass | 0.001 |  |
| `test_goto_aborts_when_odometry_stops` | pass | 0.001 |  |
| `test_goto_timeout` | pass | 0.001 |  |
| `test_cancel_goto_holds` | pass | 0.001 |  |
| `test_land_preempts_goto` | pass | 0.001 |  |
| `test_land_cannot_be_cancelled` | pass | 0.001 |  |
| `test_land_refused_on_the_ground` | pass | 0.000 |  |
| `test_hold_corrects_sag` | pass | 0.001 |  |
| `test_tilt_correction` | pass | 0.000 |  |
| `test_minus_inf_is_the_ground` | pass | 0.000 |  |
| `test_range_lost_hovers_then_resumes_hold` | pass | 0.001 |  |
| `test_range_lost_aborts_goto` | pass | 0.001 |  |
| `test_range_lost_too_long_lands_blind` | pass | 0.001 |  |
| `test_land_goal_during_autonomous_landing` | pass | 0.001 |  |
| `test_goto_feedback` | pass | 0.001 |  |
| `test_takeoff_refused_until_range_is_steady` | pass | 0.001 |  |
| `test_range_gap_restarts_the_steady_time` | pass | 0.000 |  |
| `test_range_lost_on_the_ground_during_takeoff_stays_grounded` | pass | 0.001 |  |
| `test_range_lost_mid_takeoff_holds_the_height_reached` | pass | 0.001 |  |
| `test_override_aborts_the_goal_and_goes_quiet` | pass | 0.001 |  |
| `test_goals_refused_while_overridden` | pass | 0.000 |  |
| `test_control_back_in_the_air_holds_where_it_is` | pass | 0.001 |  |
| `test_control_back_on_the_ground_stays_grounded` | pass | 0.001 |  |
| `test_override_during_land_aborts_it` | pass | 0.001 |  |
| `test_repeated_control_messages_change_nothing` | pass | 0.001 |  |
| `test_takeoff_refused_until_armed` | pass | 0.000 |  |
| `test_takeoff_refused_before_any_status` | pass | 0.000 |  |
| `test_without_radio_arming_takeoff_needs_no_arm` | pass | 0.000 |  |
| `test_stale_disarmed_status_does_not_abort_takeoff` | pass | 0.001 |  |
| `test_disarm_in_the_air_aborts_and_goes_quiet` | pass | 0.001 |  |
| `test_disarm_while_overridden_is_not_forgotten` | pass | 0.001 |  |
| `test_disarm_on_the_ground_changes_nothing` | pass | 0.000 |  |

### `drone_mission` · `test_mypy` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mypy` | pass | 3.088 |  |

### `drone_mission` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.060 |  |

### `drone_mission` · `test_xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_xmllint` | pass | 0.395 |  |

### `drone_safety` · `test_arbiter` (9)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_nothing_active_at_start` | pass | 0.000 |  |
| `test_single_source_is_forwarded` | pass | 0.000 |  |
| `test_radio_takes_over_from_mission` | pass | 0.000 |  |
| `test_manual_beats_mission_but_not_radio` | pass | 0.000 |  |
| `test_control_returns_when_the_radio_goes_quiet` | pass | 0.000 |  |
| `test_everything_quiet_is_none` | pass | 0.000 |  |
| `test_unknown_source_is_never_forwarded` | pass | 0.000 |  |
| `test_update_reports_changes_once` | pass | 0.000 |  |
| `test_time_going_backwards_is_not_fresh` | pass | 0.000 |  |

### `drone_safety` · `test_copyright` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_copyright` | skipped | 0.000 | No copyright header has been placed in the generated source file. |

### `drone_safety` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.095 |  |

### `drone_safety` · `test_mypy` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mypy` | pass | 2.987 |  |

### `drone_safety` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.018 |  |

### `drone_safety` · `test_xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_xmllint` | pass | 0.205 |  |

### `drone_sim_sensors` · `test_copyright` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_copyright` | skipped | 0.000 | No copyright header has been placed in the generated source file. |

### `drone_sim_sensors` · `test_estimator` (11)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_forward_flow_gives_forward_velocity` | pass | 0.000 |  |
| `test_left_flow_gives_left_velocity` | pass | 0.000 |  |
| `test_rotation_in_place_gives_no_velocity` | pass | 0.000 |  |
| `test_yaw_turns_body_forward_into_world_left` | pass | 0.000 |  |
| `test_integrates_position` | pass | 0.001 |  |
| `test_height_corrects_for_tilt` | pass | 0.000 |  |
| `test_too_close_reads_as_ground` | pass | 0.000 |  |
| `test_out_of_range_keeps_last_height` | pass | 0.000 |  |
| `test_lost_flow_holds_briefly_then_stops` | pass | 0.000 |  |
| `test_vertical_speed_follows_a_climb` | pass | 0.001 |  |
| `test_vertical_speed_stays_calm_in_noisy_hover` | pass | 0.004 |  |

### `drone_sim_sensors` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.124 |  |

### `drone_sim_sensors` · `test_flow_model` (11)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_hover_gives_no_flow` | pass | 0.000 |  |
| `test_forward_gives_negative_flow_y` | pass | 0.000 |  |
| `test_left_gives_positive_flow_x` | pass | 0.000 |  |
| `test_rotation_in_place_equals_body_rate` | pass | 0.000 |  |
| `test_tilt_lengthens_the_distance` | pass | 0.000 |  |
| `test_unusable_geometry_gives_none` | pass | 0.000 |  |
| `test_whole_degrees_truncate_toward_zero` | pass | 0.000 |  |
| `test_measure_passes_ideal_flow_when_clean` | pass | 0.000 |  |
| `test_measure_too_low_has_no_quality` | pass | 0.000 |  |
| `test_measure_too_fast_has_no_quality` | pass | 0.000 |  |
| `test_noise_has_the_requested_spread` | pass | 0.003 |  |

### `drone_sim_sensors` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.031 |  |

## Warnings in the output

Lines mentioning a warning (node log lines at WARN level left out: those are the behaviour under test):

```text
Warning: This process (pid=20421) is multi-threaded, use of fork() may lead to deadlocks in the child.
Warning: This process (pid=20460) is multi-threaded, use of fork() may lead to deadlocks in the child.
```

## Console summary lines

Packages are tested in parallel, so these lines interleave.

```text
Finished <<< drone_interfaces [0.30s]
================== 24 passed, 1 skipped, 32 warnings in 0.41s ==================
Finished <<< drone_sim_sensors [0.97s]
100% tests passed, 0 tests failed out of 4
Finished <<< drone_basics_cpp [1.52s]
======================== 13 passed, 1 skipped in 3.39s =========================
================== 28 passed, 1 skipped, 32 warnings in 3.97s ==================
======================== 48 passed, 1 skipped in 3.87s =========================
Finished <<< drone_safety [4.77s]
Finished <<< drone_basics_py [5.42s]
Finished <<< drone_mission [5.16s]
100% tests passed, 0 tests failed out of 6
Finished <<< drone_fc_bridge [38.6s]
100% tests passed, 0 tests failed out of 8
Summary: 8 packages finished [1min 47s]
Summary: 277 tests, 0 errors, 0 failures, 5 skipped
```

Full output: `console.log.gz` (`zcat console.log.gz | less`). Every test case, with any failure message: `results.json`.
