# Test run 2026-11-26_10205a2-dirty: PASSED

- **When:** 2026-11-26T16:21:24+00:00, on albertoPC
- **Code:** `10205a2` on `issue233/AddYolo`: resolved merge conflicts
- **Uncommitted code changes were part of this run** (2 file(s)), so the commit alone does not say what ran: `project/ros2/src/drone_perception/drone_perception/aruco_detector.py`, `project/ros2/src/drone_perception/drone_perception/yolo_detector.py`
- **Environment:** ROS jazzy, Ubuntu 24.04.5 LTS, Python 3.12.3, dev container; clean build, the same commands as CI
- **Build:** exit 0, 42 s. **ROS tests:** exit 0, 154 s. **Telemetry tests:** exit 0, 4 s

## Result

| | Test cases | Passed | Skipped | Failed |
| --- | --- | --- | --- | --- |
| Behaviour tests | 454 | 453 | 1 | 0 |
| Lint and style checks | 36 | 35 | 1 | 0 |
| **Total** | 490 | 488 | 2 | 0 |

colcon's own summary counts 510 "tests": the 490 test cases plus 20 CTest entries (one per C++ test file or linter), which wrap cases already counted.

## Compared with the previous run

Previous: `2026-11-18_7c95545-dirty-2` (`7c95545`): 458 cases, 0 failed. Now: 490 cases, 0 failed.

**New tests:**
- `drone_bringup` `pep257` `./launch/perception.launch.py`: passed
- `drone_bringup` `pep257` `./test/test_sim_sensors.py`: passed
- `drone_bringup` `pep257` `./test/test_sim_test_limits.py`: passed
- `drone_bringup` `test_sim_test_limits` `test_bands_are_ordered_shares`: passed
- `drone_bringup` `test_sim_test_limits` `test_every_limit_is_there`: passed
- `drone_bringup` `test_sim_test_limits` `test_limits_are_positive`: passed
- `drone_fc_bridge` `test_inav_state` `test_x_range_limits_as_in_the_sim`: passed
- `drone_perception` `test_copyright` `test_copyright`: skipped
- `drone_perception` `test_flake8` `test_flake8`: passed
- `drone_perception` `test_pep257` `test_pep257`: passed
- `drone_sim` `test_checks` `test_drift_compares_movement_not_positions`: passed
- `drone_sim` `test_checks` `test_drift_keeps_the_largest_error`: passed
- `drone_sim` `test_checks` `test_flow_reading_low_gives_negative_error`: passed
- `drone_sim` `test_checks` `test_mean_std`: passed
- `drone_sim` `test_checks` `test_perfect_flow_has_no_error`: passed
- `drone_sim` `test_checks` `test_unusable_flow_is_skipped`: passed
- `drone_sim` `test_floor_map` `test_default_surface_outside_every_area`: passed
- `drone_sim` `test_floor_map` `test_edges_count_as_inside`: passed
- `drone_sim` `test_floor_map` `test_inside_an_area`: passed
- `drone_sim` `test_floor_map` `test_later_area_wins_where_they_overlap`: passed
- `drone_sim` `test_floor_map` `test_the_room_map_loads`: passed
- `drone_sim` `test_floor_map` `test_unknown_surface_is_an_error`: passed
- `drone_sim` `test_flow_model` `test_plain_surface_gives_no_flow`: passed
- `drone_sim` `test_flow_model` `test_surface_quality_is_reported`: passed
- `telemetry` `test_msp_bench` `test_altitude_matches_reference`: passed
- `telemetry` `test_msp_bench` `test_analog_matches_reference`: passed
- `telemetry` `test_msp_bench` `test_attitude_matches_reference`: passed
- `telemetry` `test_msp_bench` `test_bench_run_writes_csv`: passed
- `telemetry` `test_msp_bench` `test_busy_serial_port_is_detected`: passed
- `telemetry` `test_msp_bench` `test_capture_refreshes_copies_with_the_same_name`: passed
- `telemetry` `test_msp_bench` `test_capture_replays_like_the_real_recordings`: passed
- `telemetry` `test_msp_bench` `test_error_reply_is_flagged`: passed
- `telemetry` `test_msp_bench` `test_frame_round_trip_and_crc`: passed
- `telemetry` `test_msp_bench` `test_local_pose_matches_reference`: passed
- `telemetry` `test_msp_bench` `test_logbook_run_keeps_the_wifi_rtt_columns`: passed
- `telemetry` `test_msp_bench` `test_rangefinder_matches_reference`: passed
- `telemetry` `test_msp_bench` `test_raw_imu_matches_reference`: passed
- `telemetry` `test_msp_bench` `test_rc_matches_reference`: passed
- `telemetry` `test_msp_bench` `test_status_and_arming_match_reference`: passed

**Tests no longer there:**
- `drone_bringup` `test_worlds` `test_drone_fuel_model_is_pinned[multicopter_velocity_control.sdf]`: was passed
- `drone_bringup` `test_worlds` `test_drone_has_the_fpv_camera[multicopter_velocity_control.sdf]`: was skipped
- `drone_bringup` `test_worlds` `test_drone_publishes_the_odometry_we_read[multicopter_velocity_control.sdf]`: was passed
- `drone_bringup` `test_worlds` `test_drone_starts_on_the_ground[multicopter_velocity_control.sdf]`: was passed
- `drone_bringup` `test_worlds` `test_drone_takes_our_commands[multicopter_velocity_control.sdf]`: was passed
- `drone_bringup` `test_worlds` `test_models_it_uses_exist[multicopter_velocity_control.sdf]`: was passed
- `drone_bringup` `test_worlds` `test_world_loads_physics[multicopter_velocity_control.sdf]`: was passed

## By package

| Package | Behaviour | Lint | Passed | Skipped | Failed | Time |
| --- | --- | --- | --- | --- | --- | --- |
| `drone_bringup` | 65 | 13 | 78 | 0 | 0 | 75.0 s |
| `drone_fc_bridge` | 112 | 0 | 112 | 0 | 0 | 78.0 s |
| `drone_mission` | 44 | 4 | 48 | 0 | 0 | 9.7 s |
| `drone_monitoring` | 9 | 4 | 12 | 1 | 0 | 10.0 s |
| `drone_perception` | 0 | 3 | 2 | 1 | 0 | 1.49 s |
| `drone_safety` | 9 | 4 | 13 | 0 | 0 | 9.76 s |
| `drone_sim` | 36 | 4 | 40 | 0 | 0 | 10.1 s |
| `drone_teleop` | 24 | 4 | 28 | 0 | 0 | 10.5 s |
| `telemetry` | 155 | 0 | 155 | 0 | 0 | 4 s |

## Every test

### `drone_bringup` · `flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `flake8` | pass | 0.000 |  |

### `drone_bringup` · `lint_cmake` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `CMakeLists.txt` | pass | 0.000 |  |

### `drone_bringup` · `pep257` (10)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `./launch/perception.launch.py` | pass | 0.000 |  |
| `./launch/sim.launch.py` | pass | 0.000 |  |
| `./test/fake_drone.py` | pass | 0.000 |  |
| `./test/test_config.py` | pass | 0.000 |  |
| `./test/test_launch_files.py` | pass | 0.000 |  |
| `./test/test_sim_flight.py` | pass | 0.000 |  |
| `./test/test_sim_sensors.py` | pass | 0.000 |  |
| `./test/test_sim_test_limits.py` | pass | 0.000 |  |
| `./test/test_stack.py` | pass | 0.000 |  |
| `./test/test_worlds.py` | pass | 0.000 |  |

### `drone_bringup` · `test_config` (15)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mission_climb_speed_equals_fc_limit` | pass | 0.006 |  |
| `test_safety_timeout_equals_fc_timeout` | pass | 0.000 |  |
| `test_command_within_fc_limit[mission-speed-max_speed_xy]` | pass | 0.000 |  |
| `test_command_within_fc_limit[mission-land_speed-max_speed_z]` | pass | 0.000 |  |
| `test_command_within_fc_limit[mission-yaw_rate-max_yaw_rate]` | pass | 0.000 |  |
| `test_command_within_fc_limit[radio_teleop-max_xy-max_speed_xy]` | pass | 0.000 |  |
| `test_command_within_fc_limit[radio_teleop-max_z-max_speed_z]` | pass | 0.000 |  |
| `test_command_within_fc_limit[radio_teleop-max_yaw-max_yaw_rate]` | pass | 0.000 |  |
| `test_heights_inside_rangefinder` | pass | 0.000 |  |
| `test_demo_height_inside_rangefinder` | pass | 0.000 |  |
| `test_flow_works_once_airborne` | pass | 0.000 |  |
| `test_radio_has_top_priority` | pass | 0.000 |  |
| `test_times_and_rates_positive` | pass | 0.000 |  |
| `test_decimals_are_floats` | pass | 0.000 |  |
| `test_every_section_is_a_launched_node` | pass | 0.001 |  |

### `drone_bringup` · `test_launch_files` (25)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_default_is_the_sim_with_the_radio_and_the_mission` | pass | 0.024 |  |
| `test_inav_backend_starts_no_gazebo_and_no_radio_nodes` | pass | 0.004 |  |
| `test_with_the_radio_only_the_radio_arms` | pass | 0.010 |  |
| `test_without_the_radio_the_mission_arms` | pass | 0.006 |  |
| `test_demo_flight_only_with_demo` | pass | 0.014 |  |
| `test_nothing_flies_without_a_source[source:=none demo:=false]` | pass | 0.006 |  |
| `test_nothing_flies_without_a_source[source:=none demo:=true]` | pass | 0.006 |  |
| `test_gazebo_server_and_window_are_two_processes` | pass | 0.007 |  |
| `test_headless_starts_the_server_only` | pass | 0.023 |  |
| `test_camera_picks_the_window_view` | pass | 0.025 |  |
| `test_each_source_publishes_on_its_own_topic` | pass | 0.007 |  |
| `test_watchdog_always_watches_what_fc_bridge_gets` | pass | 0.420 |  |
| `test_sim_time_only_in_the_sim` | pass | 0.420 |  |
| `test_every_node_reads_sim_yaml` | pass | 0.429 |  |
| `test_our_programs_are_installed` | pass | 0.420 |  |
| `test_other_programs_are_installed` | pass | 0.422 |  |
| `test_parameter_files_are_installed` | pass | 0.421 |  |
| `test_every_package_it_starts_is_a_dependency` | pass | 0.412 |  |
| `test_every_package_it_starts_is_checked_first` | pass | 0.411 |  |
| `test_a_missing_package_stops_the_launch[drone_mission]` | pass | 0.001 |  |
| `test_a_missing_package_stops_the_launch[drone_fc_bridge]` | pass | 0.001 |  |
| `test_a_missing_package_stops_the_launch[ros_gz_bridge]` | pass | 0.001 |  |
| `test_a_missing_package_stops_the_launch[joy]` | pass | 0.002 |  |
| `test_the_real_drone_needs_none_of_the_sim_packages` | pass | 0.004 |  |
| `test_refuses_to_start_next_to_a_running_sim` | pass | 0.005 |  |

### `drone_bringup` · `test_sim_test_limits` (3)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_every_limit_is_there` | pass | 0.002 |  |
| `test_limits_are_positive` | pass | 0.001 |  |
| `test_bands_are_ordered_shares` | pass | 0.001 |  |

### `drone_bringup` · `test_stack` (5)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_disarm_mid_flight` | pass | 8.721 |  |
| `test_disarm_while_the_radio_flies` | pass | 7.681 |  |
| `test_full_flight` | pass | 26.981 |  |
| `test_radio_takes_over_and_gives_back` | pass | 18.237 |  |
| `test_takeoff_refused_until_armed` | pass | 1.244 |  |

### `drone_bringup` · `test_worlds` (17)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_bridge_talks_to_one_drone` | pass | 0.002 |  |
| `test_world_loads_physics[outdoor_field.sdf]` | pass | 0.003 |  |
| `test_world_loads_physics[room_world.sdf]` | pass | 0.001 |  |
| `test_drone_takes_our_commands[outdoor_field.sdf]` | pass | 0.004 |  |
| `test_drone_takes_our_commands[room_world.sdf]` | pass | 0.001 |  |
| `test_drone_publishes_the_odometry_we_read[outdoor_field.sdf]` | pass | 0.003 |  |
| `test_drone_publishes_the_odometry_we_read[room_world.sdf]` | pass | 0.001 |  |
| `test_drone_starts_on_the_ground[outdoor_field.sdf]` | pass | 0.003 |  |
| `test_drone_starts_on_the_ground[room_world.sdf]` | pass | 0.001 |  |
| `test_drone_fuel_model_is_pinned[outdoor_field.sdf]` | pass | 0.003 |  |
| `test_drone_fuel_model_is_pinned[room_world.sdf]` | pass | 0.001 |  |
| `test_models_it_uses_exist[outdoor_field.sdf]` | pass | 0.003 |  |
| `test_models_it_uses_exist[room_world.sdf]` | pass | 0.001 |  |
| `test_drone_has_the_fpv_camera[outdoor_field.sdf]` | pass | 0.003 |  |
| `test_drone_has_the_fpv_camera[room_world.sdf]` | pass | 0.001 |  |
| `test_every_model_has_its_files` | pass | 0.003 |  |
| `test_worlds_and_models_are_installed` | pass | 0.001 |  |

### `drone_bringup` · `xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `package.xml` | pass | 0.000 |  |

### `drone_fc_bridge` · `test_inav_decode` (22)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `ApiVersion` | pass | 0.000 |  |
| `FcVariant` | pass | 0.000 |  |
| `FcVersion` | pass | 0.000 |  |
| `RangefinderFromCaptures` | pass | 0.000 |  |
| `RangefinderStates` | pass | 0.000 |  |
| `RcFromCaptures` | pass | 0.007 |  |
| `RcHandBuilt` | pass | 0.000 |  |
| `MotorsFromCapture` | pass | 0.000 |  |
| `MotorsHandBuilt` | pass | 0.000 |  |
| `BoxNamesFromCapture` | pass | 0.001 |  |
| `BoxNamesHandBuilt` | pass | 0.000 |  |
| `Attitude` | pass | 0.000 |  |
| `AttitudeLimits` | pass | 0.000 |  |
| `Status` | pass | 0.000 |  |
| `StatusInEveryCapture` | pass | 0.005 |  |
| `StatusHandBuilt` | pass | 0.000 |  |
| `OpticalFlow` | pass | 0.000 |  |
| `OpticalFlowHandBuilt` | pass | 0.000 |  |
| `Analog` | pass | 0.000 |  |
| `AnalogHandBuilt` | pass | 0.000 |  |
| `LocalPose` | pass | 0.000 |  |
| `LocalPoseHandBuilt` | pass | 0.000 |  |

### `drone_fc_bridge` · `test_inav_link` (13)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `PollsAndDecodes` | pass | 0.273 |  |
| `AsksForTheModeListUntilItHasOne` | pass | 1.611 |  |
| `SendsTheSticksEveryCycleWhileTheyAreFresh` | pass | 1.179 |  |
| `StopsSendingWhenTheSticksGoStale` | pass | 0.606 |  |
| `StopsSendingAtOnceOnNullopt` | pass | 0.455 |  |
| `NoSticksWhileTheLinkIsDown` | pass | 0.556 |  |
| `ModeOnFromTheStatusBit` | pass | 0.000 |  |
| `SendsTheCycleAtOnce` | pass | 0.354 |  |
| `SurvivesDroppedRepliesAndRubbish` | pass | 1.656 |  |
| `ReconnectsWhenTheLinkGoesSilent` | pass | 0.906 |  |
| `ReconnectsWhenTheBridgeHangsUp` | pass | 0.324 |  |
| `StopsWhenTheFcIsNotInav` | pass | 0.256 |  |
| `StopIsPromptWithNothingListening` | pass | 0.104 |  |

### `drone_fc_bridge` · `test_inav_sticks` (9)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `ZeroIsCentred` | pass | 0.000 |  |
| `EachSign` | pass | 0.000 |  |
| `FullScaleIsFullStick` | pass | 0.000 |  |
| `FasterIsClampedToFullStick` | pass | 0.000 |  |
| `FullScaleComesFromTheConfig` | pass | 0.000 |  |
| `RoundsToTheNearestMicrosecond` | pass | 0.000 |  |
| `AlwaysInsideWhatTheBuilderTakes` | pass | 0.001 |  |
| `NonFiniteSetpointIsCentred` | pass | 0.000 |  |
| `RefusesABadConfig` | pass | 0.000 |  |

### `drone_fc_bridge` · `test_msp` (24)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `StandardCheckValue` | pass | 0.000 |  |
| `MatchesCapturedFrames` | pass | 0.000 |  |
| `SameBytesAsPython` | pass | 0.000 |  |
| `OnlyReadCommands` | pass | 0.000 |  |
| `PayloadAndItsLimit` | pass | 0.000 |  |
| `SameBytesAsPython` | pass | 0.000 |  |
| `ExactlyFourChannelsInAetrOrder` | pass | 0.000 |  |
| `RefusesValuesOutsideTheStickRange` | pass | 0.000 |  |
| `EveryGoodFrameParses` | pass | 0.009 |  |
| `DamagedFramesAreNotReturned` | pass | 0.005 |  |
| `WholeFileAsOneStream` | pass | 0.023 |  |
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
| `DrainsABigBacklogInLinearTime` | pass | 0.080 |  |
| `FeedAfterPartialDrainKeepsOrder` | pass | 0.000 |  |

### `drone_fc_bridge` · `test_failsafes` (9)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_fresh_setpoint_is_forwarded` | pass | 1.810 |  |
| `test_horizontal_clamp_keeps_direction` | pass | 1.819 |  |
| `test_inf_is_rejected` | pass | 1.820 |  |
| `test_nan_is_rejected_and_times_out` | pass | 2.310 |  |
| `test_roll_and_pitch_rates_are_zeroed` | pass | 1.808 |  |
| `test_sim_enable_is_published` | pass | 2.311 |  |
| `test_timeout_sends_zero` | pass | 2.811 |  |
| `test_vertical_and_yaw_clamp` | pass | 2.821 |  |
| `test_zero_without_setpoints` | pass | 1.818 |  |

### `drone_fc_bridge` · `test_inav` (3)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_arm_is_refused` | pass | 0.003 |  |
| `test_nothing_reaches_the_sim` | pass | 0.000 |  |
| `test_status_says_inav_and_disarmed` | pass | 0.000 |  |

### `drone_fc_bridge` · `test_inav_rc` (7)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_a_no_setpoint_sends_centred_sticks` | pass | 1.050 |  |
| `test_b_each_axis_in_aetr_order_with_ros_signs` | pass | 4.151 |  |
| `test_c_clamped_to_the_speed_limits` | pass | 1.049 |  |
| `test_d_setpoint_timeout_centres` | pass | 2.051 |  |
| `test_e_hold_centres` | pass | 1.050 |  |
| `test_f_fc_rc_and_status_follow_the_override_switch` | pass | 2.099 |  |
| `test_g_only_reads_and_sticks` | pass | 0.000 |  |

### `drone_fc_bridge` · `test_inav_state` (13)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_a_status_armed_and_link_ok` | pass | 0.000 |  |
| `test_b_attitude_in_ros_convention` | pass | 0.000 |  |
| `test_c_odom_position_north_west_up` | pass | 0.000 |  |
| `test_d_odom_velocity_in_the_body_frame` | pass | 0.000 |  |
| `test_e_range` | pass | 0.000 |  |
| `test_f_optical_flow_passes_through` | pass | 0.000 |  |
| `test_g_battery` | pass | 0.000 |  |
| `test_h_only_reads_were_asked` | pass | 0.000 |  |
| `test_i_rc_read_back_and_no_sticks_sent` | pass | 0.000 |  |
| `test_j_motors` | pass | 0.000 |  |
| `test_x_range_limits_as_in_the_sim` | pass | 2.599 |  |
| `test_y_no_rangefinder_bit_means_no_range` | pass | 1.549 |  |
| `test_z_silence_marks_the_link_down` | pass | 2.002 |  |

### `drone_fc_bridge` · `test_services` (4)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_disarm_and_rearm` | pass | 3.020 |  |
| `test_hold_sends_zero_despite_setpoints` | pass | 1.521 |  |
| `test_starts_armed` | pass | 0.000 |  |
| `test_status_reports_setpoint_age` | pass | 1.459 |  |

### `drone_fc_bridge` · `test_state` (7)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_body_velocity_rotated_by_heading` | pass | 1.524 |  |
| `test_height_and_orientation_from_sim` | pass | 0.415 |  |
| `test_position_is_integrated_not_copied` | pass | 1.527 |  |
| `test_range_level` | pass | 0.414 |  |
| `test_range_out_of_range_is_inf` | pass | 1.238 |  |
| `test_range_reads_longer_when_tilted` | pass | 0.411 |  |
| `test_velocity_passes_through` | pass | 0.614 |  |

### `drone_fc_bridge` · `test_watchdog` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_warns_when_the_stream_stops_and_when_it_is_back` | pass | 1.996 |  |

### `drone_mission` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.310 |  |

### `drone_mission` · `test_logic` (44)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_starts_grounded_and_silent` | pass | 0.002 |  |
| `test_takeoff_hold_land` | pass | 0.003 |  |
| `test_takeoff_to_a_given_height` | pass | 0.002 |  |
| `test_takeoff_refused_without_range` | pass | 0.001 |  |
| `test_takeoff_refused_above_range_max` | pass | 0.001 |  |
| `test_takeoff_refused_in_the_air` | pass | 0.002 |  |
| `test_takeoff_timeout_lands` | pass | 0.003 |  |
| `test_cancel_takeoff_holds_where_it_is` | pass | 0.002 |  |
| `test_goto_forward` | pass | 0.003 |  |
| `test_goto_is_relative_to_heading` | pass | 0.003 |  |
| `test_goto_square_comes_back` | pass | 0.007 |  |
| `test_goto_refused_on_the_ground_and_during_takeoff` | pass | 0.001 |  |
| `test_goto_refused_without_odometry` | pass | 0.002 |  |
| `test_goto_aborts_when_odometry_stops` | pass | 0.002 |  |
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
| `test_land_goal_during_autonomous_landing` | pass | 0.003 |  |
| `test_goto_feedback` | pass | 0.002 |  |
| `test_takeoff_refused_until_range_is_steady` | pass | 0.001 |  |
| `test_range_gap_restarts_the_steady_time` | pass | 0.001 |  |
| `test_range_lost_on_the_ground_during_takeoff_stays_grounded` | pass | 0.002 |  |
| `test_range_lost_mid_takeoff_holds_the_height_reached` | pass | 0.002 |  |
| `test_override_aborts_the_goal_and_goes_quiet` | pass | 0.002 |  |
| `test_goals_refused_while_overridden` | pass | 0.001 |  |
| `test_control_back_in_the_air_holds_where_it_is` | pass | 0.003 |  |
| `test_control_back_on_the_ground_stays_grounded` | pass | 0.003 |  |
| `test_override_during_land_aborts_it` | pass | 0.002 |  |
| `test_repeated_control_messages_change_nothing` | pass | 0.002 |  |
| `test_takeoff_refused_until_armed` | pass | 0.001 |  |
| `test_takeoff_refused_before_any_status` | pass | 0.001 |  |
| `test_without_radio_arming_takeoff_needs_no_arm` | pass | 0.001 |  |
| `test_stale_disarmed_status_does_not_abort_takeoff` | pass | 0.001 |  |
| `test_disarm_in_the_air_aborts_and_goes_quiet` | pass | 0.001 |  |
| `test_disarm_while_overridden_is_not_forgotten` | pass | 0.002 |  |
| `test_disarm_on_the_ground_changes_nothing` | pass | 0.001 |  |

### `drone_mission` · `test_mypy` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mypy` | pass | 6.184 |  |

### `drone_mission` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.095 |  |

### `drone_mission` · `test_xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_xmllint` | pass | 0.343 |  |

### `drone_monitoring` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.235 |  |

### `drone_monitoring` · `test_metrics` (9)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_nothing_received_means_no_values` | pass | 0.001 |  |
| `test_status_values` | pass | 0.063 |  |
| `test_no_age_yet_is_no_sample` | pass | 0.001 |  |
| `test_quiet_topic_drops_its_values_but_keeps_its_counter` | pass | 0.001 |  |
| `test_range_out_of_limits_is_no_sample` | pass | 0.001 |  |
| `test_battery` | pass | 0.001 |  |
| `test_active_source_switches` | pass | 0.001 |  |
| `test_counts_messages_per_topic` | pass | 0.001 |  |
| `test_every_metric_the_dashboard_queries_exists` | skipped | 0.001 | /home/monitoring/grafana/dashboards/drone.json not here (the dev container mounts only project/) |

### `drone_monitoring` · `test_mypy` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mypy` | pass | 6.238 |  |

### `drone_monitoring` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.030 |  |

### `drone_monitoring` · `test_xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_xmllint` | pass | 0.377 |  |

### `drone_perception` · `test_copyright` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_copyright` | skipped | 0.000 | No copyright header has been placed in the generated source file. |

### `drone_perception` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.212 |  |

### `drone_perception` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.036 |  |

### `drone_safety` · `test_arbiter` (9)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_nothing_active_at_start` | pass | 0.001 |  |
| `test_single_source_is_forwarded` | pass | 0.001 |  |
| `test_radio_takes_over_from_mission` | pass | 0.000 |  |
| `test_manual_beats_mission_but_not_radio` | pass | 0.000 |  |
| `test_control_returns_when_the_radio_goes_quiet` | pass | 0.000 |  |
| `test_everything_quiet_is_none` | pass | 0.000 |  |
| `test_unknown_source_is_never_forwarded` | pass | 0.000 |  |
| `test_update_reports_changes_once` | pass | 0.000 |  |
| `test_time_going_backwards_is_not_fresh` | pass | 0.001 |  |

### `drone_safety` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.164 |  |

### `drone_safety` · `test_mypy` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mypy` | pass | 6.172 |  |

### `drone_safety` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.027 |  |

### `drone_safety` · `test_xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_xmllint` | pass | 0.766 |  |

### `drone_sim` · `test_checks` (6)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mean_std` | pass | 0.001 |  |
| `test_perfect_flow_has_no_error` | pass | 0.001 |  |
| `test_flow_reading_low_gives_negative_error` | pass | 0.001 |  |
| `test_unusable_flow_is_skipped` | pass | 0.000 |  |
| `test_drift_compares_movement_not_positions` | pass | 0.000 |  |
| `test_drift_keeps_the_largest_error` | pass | 0.000 |  |

### `drone_sim` · `test_estimator` (11)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_forward_flow_gives_forward_velocity` | pass | 0.001 |  |
| `test_left_flow_gives_left_velocity` | pass | 0.000 |  |
| `test_rotation_in_place_gives_no_velocity` | pass | 0.000 |  |
| `test_yaw_turns_body_forward_into_world_left` | pass | 0.000 |  |
| `test_integrates_position` | pass | 0.002 |  |
| `test_height_corrects_for_tilt` | pass | 0.000 |  |
| `test_too_close_reads_as_ground` | pass | 0.000 |  |
| `test_out_of_range_keeps_last_height` | pass | 0.000 |  |
| `test_lost_flow_holds_briefly_then_stops` | pass | 0.000 |  |
| `test_vertical_speed_follows_a_climb` | pass | 0.002 |  |
| `test_vertical_speed_stays_calm_in_noisy_hover` | pass | 0.006 |  |

### `drone_sim` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.258 |  |

### `drone_sim` · `test_floor_map` (6)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_default_surface_outside_every_area` | pass | 0.001 |  |
| `test_inside_an_area` | pass | 0.001 |  |
| `test_later_area_wins_where_they_overlap` | pass | 0.001 |  |
| `test_edges_count_as_inside` | pass | 0.001 |  |
| `test_unknown_surface_is_an_error` | pass | 0.001 |  |
| `test_the_room_map_loads` | pass | 0.011 |  |

### `drone_sim` · `test_flow_model` (13)

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
| `test_measure_too_fast_has_no_quality` | pass | 0.000 |  |
| `test_noise_has_the_requested_spread` | pass | 0.006 |  |
| `test_surface_quality_is_reported` | pass | 0.000 |  |
| `test_plain_surface_gives_no_flow` | pass | 0.000 |  |

### `drone_sim` · `test_mypy` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mypy` | pass | 6.128 |  |

### `drone_sim` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.067 |  |

### `drone_sim` · `test_xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_xmllint` | pass | 0.301 |  |

### `drone_teleop` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.278 |  |

### `drone_teleop` · `test_mypy` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mypy` | pass | 5.706 |  |

### `drone_teleop` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.047 |  |

### `drone_teleop` · `test_radio_teleop` (24)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_switch_off_publishes_nothing` | pass | 0.130 |  |
| `test_engage_after_hold` | pass | 0.072 |  |
| `test_no_engage_before_hold` | pass | 0.016 |  |
| `test_bounce_while_arming_does_not_engage` | pass | 0.015 |  |
| `test_engages_once_bounce_settles` | pass | 0.017 |  |
| `test_off_is_immediate` | pass | 0.018 |  |
| `test_bounce_while_disarming_does_not_reengage` | pass | 0.017 |  |
| `test_engage_refused_with_throttle_off_centre` | pass | 0.016 |  |
| `test_throttle_moves_freely_once_engaged` | pass | 0.017 |  |
| `test_sticks_scaled_to_limits` | pass | 0.017 |  |
| `test_deadband_gives_zero` | pass | 0.017 |  |
| `test_reengage_needs_throttle_centred_again` | pass | 0.020 |  |
| `test_switch_at_threshold_is_off` | pass | 0.016 |  |
| `test_missing_arm_axis_is_off` | pass | 0.016 |  |
| `test_arm_switch_arms_the_fc_once` | pass | 0.020 |  |
| `test_arm_switch_off_disarms_even_in_flight` | pass | 0.019 |  |
| `test_arm_switch_on_at_start_must_be_cycled` | pass | 0.018 |  |
| `test_arming_refused_with_throttle_off_centre` | pass | 0.018 |  |
| `test_arm_alone_does_not_take_over` | pass | 0.018 |  |
| `test_takeover_alone_does_nothing` | pass | 0.016 |  |
| `test_takeover_with_arm_on_engages_after_hold` | pass | 0.018 |  |
| `test_takeover_off_releases_at_once` | pass | 0.018 |  |
| `test_arm_off_releases_even_with_takeover_on` | pass | 0.019 |  |
| `test_missing_takeover_axis_is_off` | pass | 0.017 |  |

### `drone_teleop` · `test_xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_xmllint` | pass | 0.287 |  |

### `telemetry` · `test_capture_copies` (2)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_recordings_are_where_this_test_looks` | pass | 0.001 |  |
| `test_copies_in_ros2_match_the_recordings` | pass | 0.004 |  |

### `telemetry` · `test_captures` (47)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_recording_header[flat_still]` | pass | 0.001 |  |
| `test_recording_header[tilted]` | pass | 0.001 |  |
| `test_recording_header[radio_off]` | pass | 0.001 |  |
| `test_recording_header[flow_moving]` | pass | 0.001 |  |
| `test_timeouts_have_no_frame[flat_still]` | pass | 0.001 |  |
| `test_timeouts_have_no_frame[tilted]` | pass | 0.001 |  |
| `test_timeouts_have_no_frame[radio_off]` | pass | 0.001 |  |
| `test_timeouts_have_no_frame[flow_moving]` | pass | 0.001 |  |
| `test_every_good_reply_is_whole_with_a_valid_crc[flat_still]` | pass | 0.005 |  |
| `test_every_good_reply_is_whole_with_a_valid_crc[tilted]` | pass | 0.005 |  |
| `test_every_good_reply_is_whole_with_a_valid_crc[radio_off]` | pass | 0.005 |  |
| `test_every_good_reply_is_whole_with_a_valid_crc[flow_moving]` | pass | 0.005 |  |
| `test_parser_reads_every_good_reply[flat_still]` | pass | 0.006 |  |
| `test_parser_reads_every_good_reply[tilted]` | pass | 0.005 |  |
| `test_parser_reads_every_good_reply[radio_off]` | pass | 0.005 |  |
| `test_parser_reads_every_good_reply[flow_moving]` | pass | 0.005 |  |
| `test_parser_rejects_every_damaged_reply[flat_still]` | pass | 0.002 |  |
| `test_parser_rejects_every_damaged_reply[tilted]` | pass | 0.001 |  |
| `test_parser_rejects_every_damaged_reply[radio_off]` | pass | 0.001 |  |
| `test_parser_rejects_every_damaged_reply[flow_moving]` | pass | 0.001 |  |
| `test_every_good_reply_decodes_fully[flat_still]` | pass | 0.002 |  |
| `test_every_good_reply_decodes_fully[tilted]` | pass | 0.002 |  |
| `test_every_good_reply_decodes_fully[radio_off]` | pass | 0.001 |  |
| `test_every_good_reply_decodes_fully[flow_moving]` | pass | 0.002 |  |
| `test_flat_still_is_level` | pass | 0.002 |  |
| `test_tilted_rolls_about_46_degrees[tilted]` | pass | 0.004 |  |
| `test_radio_off_is_failsafe[radio_off]` | pass | 0.003 |  |
| `test_flow_moving_sees_motion` | pass | 0.001 |  |
| `test_still_states_have_little_flow[flat_still]` | pass | 0.001 |  |
| `test_still_states_have_little_flow[tilted]` | pass | 0.001 |  |
| `test_still_states_have_little_flow[radio_off]` | pass | 0.001 |  |
| `test_identity[flat_still]` | pass | 0.003 |  |
| `test_identity[tilted]` | pass | 0.004 |  |
| `test_identity[radio_off]` | pass | 0.003 |  |
| `test_identity[flow_moving]` | pass | 0.003 |  |
| `test_mode_names[flat_still]` | pass | 0.001 |  |
| `test_mode_names[tilted]` | pass | 0.001 |  |
| `test_mode_names[radio_off]` | pass | 0.001 |  |
| `test_mode_names[flow_moving]` | pass | 0.001 |  |
| `test_disarmed_on_the_bench_without_a_rangefinder[flat_still]` | pass | 0.003 |  |
| `test_disarmed_on_the_bench_without_a_rangefinder[tilted]` | pass | 0.003 |  |
| `test_disarmed_on_the_bench_without_a_rangefinder[radio_off]` | pass | 0.003 |  |
| `test_disarmed_on_the_bench_without_a_rangefinder[flow_moving]` | pass | 0.003 |  |
| `test_battery[flat_still]` | pass | 0.001 |  |
| `test_battery[tilted]` | pass | 0.001 |  |
| `test_battery[radio_off]` | pass | 0.001 |  |
| `test_battery[flow_moving]` | pass | 0.001 |  |

### `telemetry` · `test_decoders` (59)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_attitude_tenths_of_a_degree` | pass | 0.000 |  |
| `test_altitude_cm_to_m` | pass | 0.000 |  |
| `test_raw_imu_axis_order` | pass | 0.000 |  |
| `test_opflow_signed_rates` | pass | 0.000 |  |
| `test_msp_analog_scaling` | pass | 0.000 |  |
| `test_inav_analog_scaling_and_flags` | pass | 0.000 |  |
| `test_every_battery_state[0-ok]` | pass | 0.000 |  |
| `test_every_battery_state[1-warning]` | pass | 0.000 |  |
| `test_every_battery_state[2-critical]` | pass | 0.000 |  |
| `test_every_battery_state[3-not_present]` | pass | 0.000 |  |
| `test_rangefinder_cm_to_m` | pass | 0.000 |  |
| `test_rangefinder_minus_one_is_out_of_range` | pass | 0.000 |  |
| `test_raw_gps_degrees_and_optional_hdop` | pass | 0.000 |  |
| `test_comp_gps` | pass | 0.000 |  |
| `test_u16_list_ignores_a_trailing_odd_byte` | pass | 0.000 |  |
| `test_text_strips_padding` | pass | 0.000 |  |
| `test_box_names_split` | pass | 0.000 |  |
| `test_sensor_bits` | pass | 0.000 |  |
| `test_armed_bit_is_not_a_blocker` | pass | 0.000 |  |
| `test_arming_blockers_named_in_bit_order` | pass | 0.000 |  |
| `test_flight_modes_from_names` | pass | 0.000 |  |
| `test_flight_mode_without_a_name` | pass | 0.000 |  |
| `test_inav_status_fields` | pass | 0.000 |  |
| `test_inav_status_without_mixer_profile` | pass | 0.000 |  |
| `test_status_and_status_ex` | pass | 0.000 |  |
| `test_identity` | pass | 0.000 |  |
| `test_drone_mode_names` | pass | 0.000 |  |
| `test_real_attitude[24583e006c000600f7ffc0ff300089--0.9--6.4-48]` | pass | 0.000 |  |
| `test_real_attitude[24583e006c000600d20188ff650184-46.6--12.0-357]` | pass | 0.000 |  |
| `test_real_attitude[24583e006c000600ddffbfff01001d--3.5--6.5-1]` | pass | 0.000 |  |
| `test_real_imu_agrees_with_the_tilt` | pass | 0.000 |  |
| `test_real_status_flat` | pass | 0.000 |  |
| `test_real_status_tilted_is_not_level` | pass | 0.000 |  |
| `test_real_battery` | pass | 0.000 |  |
| `test_real_optical_flow_while_moving` | pass | 0.000 |  |
| `test_only_real_arming_blockers_are_listed` | pass | 0.000 |  |
| `test_rangefinder_zero_is_not_a_distance` | pass | 0.000 |  |
| `test_inav_analog_negative_power_and_drawn` | pass | 0.000 |  |
| `test_real_rc_and_motors` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[attitude]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[altitude]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[imu_raw]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[rc_channels]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[motors]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[inav_status]` | pass | 0.002 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[inav_analog]` | pass | 0.001 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[opflow]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[rangefinder]` | pass | 0.001 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[local_pose]` | pass | 0.001 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[nav_status]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[link_stats]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[api_version]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[fc_variant]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[fc_version]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[board_info]` | pass | 0.001 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[craft_name]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[mode_names]` | pass | 0.000 |  |
| `test_command_numbers` | pass | 0.000 |  |
| `test_raw_payload_is_hex_in_json_and_decimal_on_screen` | pass | 0.000 |  |

### `telemetry` · `test_msp_bench` (15)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_raw_imu_matches_reference` | pass | 0.004 |  |
| `test_attitude_matches_reference` | pass | 0.004 |  |
| `test_altitude_matches_reference` | pass | 0.004 |  |
| `test_analog_matches_reference` | pass | 0.004 |  |
| `test_status_and_arming_match_reference` | pass | 0.004 |  |
| `test_rangefinder_matches_reference` | pass | 0.004 |  |
| `test_local_pose_matches_reference` | pass | 0.004 |  |
| `test_rc_matches_reference` | pass | 0.004 |  |
| `test_frame_round_trip_and_crc` | pass | 0.000 |  |
| `test_error_reply_is_flagged` | pass | 0.000 |  |
| `test_bench_run_writes_csv` | pass | 2.791 |  |
| `test_logbook_run_keeps_the_wifi_rtt_columns` | pass | 0.288 |  |
| `test_capture_replays_like_the_real_recordings` | pass | 0.232 |  |
| `test_capture_refreshes_copies_with_the_same_name` | pass | 0.002 |  |
| `test_busy_serial_port_is_detected` | pass | 0.056 |  |

### `telemetry` · `test_msp_frame` (32)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_crc_standard_check_value` | pass | 0.000 |  |
| `test_crc_of_nothing_is_zero` | pass | 0.000 |  |
| `test_crc_matches_real_drone_frames[24583e0001000300000205a6]` | pass | 0.000 |  |
| `test_crc_matches_real_drone_frames[24583e0002000400494e415694]` | pass | 0.000 |  |
| `test_crc_matches_real_drone_frames[24583e006c000600f7ffc0ff300089]` | pass | 0.001 |  |
| `test_crc_matches_real_drone_frames[24583e0000201600ff013200a3000d00000002041000000200000000000007]` | pass | 0.001 |  |
| `test_crc_matches_real_drone_frames[24583e00022018004050063e00e90300000c000000cf0000000000000052000072]` | pass | 0.001 |  |
| `test_crc_matches_real_drone_frames[24583e00012009005c2e00090000000000c3]` | pass | 0.000 |  |
| `test_crc_detects_a_single_flipped_bit` | pass | 0.001 |  |
| `test_request_frame_layout` | pass | 0.000 |  |
| `test_request_frame_with_payload` | pass | 0.000 |  |
| `test_v2_command_ids_are_two_bytes_little_endian[1-1-0]` | pass | 0.000 |  |
| `test_v2_command_ids_are_two_bytes_little_endian[8192-0-32]` | pass | 0.000 |  |
| `test_v2_command_ids_are_two_bytes_little_endian[8193-1-32]` | pass | 0.000 |  |
| `test_v2_command_ids_are_two_bytes_little_endian[8736-32-34]` | pass | 0.000 |  |
| `test_request_matches_the_reply_header` | pass | 0.000 |  |
| `test_parses_a_real_reply` | pass | 0.000 |  |
| `test_back_to_back_replies_come_out_in_order` | pass | 0.000 |  |
| `test_garbage_before_a_frame_is_skipped` | pass | 0.000 |  |
| `test_bad_crc_is_dropped_and_the_next_frame_still_parses` | pass | 0.001 |  |
| `test_error_reply_is_reported_not_ok` | pass | 0.000 |  |
| `test_own_request_echoed_back_is_ignored` | pass | 0.000 |  |
| `test_impossible_size_is_skipped` | pass | 0.000 |  |
| `test_incomplete_frame_waits_for_the_rest` | pass | 0.000 |  |
| `test_marker_split_across_two_reads` | pass | 0.000 |  |
| `test_valid_reply_inside_a_corrupt_one_is_recovered` | pass | 0.001 |  |
| `test_request_sends_the_frame_and_returns_the_payload` | pass | 0.000 |  |
| `test_reply_split_over_several_reads` | pass | 0.000 |  |
| `test_stale_reply_to_another_command_is_skipped` | pass | 0.000 |  |
| `test_error_reply_returns_not_ok` | pass | 0.000 |  |
| `test_no_reply_times_out` | pass | 0.202 |  |
| `test_closed_connection_raises` | pass | 0.001 |  |

## Warnings in the output

Lines mentioning a warning (node log lines at WARN level left out: those are the behaviour under test):

```text
../project/telemetry/tests/test_decoders.py::test_every_battery_state[1-warning] PASSED [ 36%]
Warning: This process (pid=1479) is multi-threaded, use of fork() may lead to deadlocks in the child.
Warning: This process (pid=1557) is multi-threaded, use of fork() may lead to deadlocks in the child.
```

## Console summary lines

Packages are tested in parallel, so these lines interleave.

```text
Finished <<< drone_interfaces [0.70s]
========================= 2 passed, 1 skipped in 0.35s =========================
Finished <<< drone_perception [1.49s]
============================== 13 passed in 7.29s ==============================
======================= 28 passed, 16 warnings in 7.52s ========================
============================== 48 passed in 7.25s ==============================
======================== 12 passed, 1 skipped in 7.34s =========================
======================= 40 passed, 16 warnings in 7.28s ========================
Finished <<< drone_safety [9.76s]
Finished <<< drone_mission [9.70s]
Finished <<< drone_teleop [10.5s]
Finished <<< drone_monitoring [10.0s]
Finished <<< drone_sim [10.1s]
100% tests passed, 0 tests failed out of 11
100% tests passed, 0 tests failed out of 9
Summary: 9 packages finished [2min 34s]
Summary: 355 tests, 0 errors, 0 failures, 2 skipped
```

Full output: `console.log.gz` (`zcat console.log.gz | less`). Every test case, with any failure message: `results.json`.
