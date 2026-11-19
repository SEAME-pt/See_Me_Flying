# Test run 2026-11-18_5957765-dirty-2: PASSED

- **When:** 2026-11-18T12:28:41+00:00, on seame-10
- **Code:** `5957765` on `copy-nando`: deletion and reorganization of ros2 files
- **Uncommitted code changes were part of this run** (115 file(s)), so the commit alone does not say what ran: `project/ros2/src/drone_bringup/CMakeLists.txt`, `project/ros2/src/drone_bringup/config/gz_bridge.yaml`, `project/ros2/src/drone_bringup/config/sim.yaml`, `project/ros2/src/drone_bringup/launch/sim.launch.py`, `project/ros2/src/drone_bringup/models/grass_ground/materials/textures/grass.jpg`, `project/ros2/src/drone_bringup/models/grass_ground/model.config`, `project/ros2/src/drone_bringup/models/grass_ground/model.sdf`, `project/ros2/src/drone_bringup/models/room/meshes/room.stl`, `project/ros2/src/drone_bringup/models/room/model.config`, `project/ros2/src/drone_bringup/models/room/model.sdf`, `project/ros2/src/drone_bringup/package.xml`, `project/ros2/src/drone_bringup/test/fake_drone.py`, `project/ros2/src/drone_bringup/test/test_config.py`, `project/ros2/src/drone_bringup/test/test_launch_files.py`, `project/ros2/src/drone_bringup/test/test_sim_flight.py`, `project/ros2/src/drone_bringup/test/test_stack.py`, `project/ros2/src/drone_bringup/test/test_worlds.py`, `project/ros2/src/drone_bringup/worlds/outdoor_field.sdf`, `project/ros2/src/drone_bringup/worlds/room_world.sdf`, `project/ros2/src/drone_fc_bridge/CMakeLists.txt`, `project/ros2/src/drone_fc_bridge/package.xml`, `project/ros2/src/drone_fc_bridge/src/fc_bridge.cpp`, `project/ros2/src/drone_fc_bridge/src/inav_decode.cpp`, `project/ros2/src/drone_fc_bridge/src/inav_decode.hpp`, `project/ros2/src/drone_fc_bridge/src/msp.cpp`, `project/ros2/src/drone_fc_bridge/src/msp.hpp`, `project/ros2/src/drone_fc_bridge/test/capture.hpp`, `project/ros2/src/drone_fc_bridge/test/data/flat_still.jsonl`, `project/ros2/src/drone_fc_bridge/test/data/flow_moving.jsonl`, `project/ros2/src/drone_fc_bridge/test/data/radio_off.jsonl`, `project/ros2/src/drone_fc_bridge/test/data/tilted.jsonl`, `project/ros2/src/drone_fc_bridge/test/test_failsafes.py`, `project/ros2/src/drone_fc_bridge/test/test_inav.py`, `project/ros2/src/drone_fc_bridge/test/test_inav_decode.cpp`, `project/ros2/src/drone_fc_bridge/test/test_msp.cpp`, `project/ros2/src/drone_fc_bridge/test/test_services.py`, `project/ros2/src/drone_fc_bridge/test/test_state.py`, `project/ros2/src/drone_interfaces/CMakeLists.txt`, `project/ros2/src/drone_interfaces/action/Goto.action`, `project/ros2/src/drone_interfaces/action/Land.action`, `project/ros2/src/drone_interfaces/action/Takeoff.action`, `project/ros2/src/drone_interfaces/msg/FcStatus.msg`, `project/ros2/src/drone_interfaces/msg/OpticalFlow.msg`, `project/ros2/src/drone_interfaces/package.xml`, `project/ros2/src/drone_mission/drone_mission/__init__.py`, `project/ros2/src/drone_mission/drone_mission/demo_flight.py`, `project/ros2/src/drone_mission/drone_mission/logic.py`, `project/ros2/src/drone_mission/drone_mission/mission.py`, `project/ros2/src/drone_mission/package.xml`, `project/ros2/src/drone_mission/resource/drone_mission`, `project/ros2/src/drone_mission/setup.cfg`, `project/ros2/src/drone_mission/setup.py`, `project/ros2/src/drone_mission/test/test_flake8.py`, `project/ros2/src/drone_mission/test/test_logic.py`, `project/ros2/src/drone_mission/test/test_mypy.py`, `project/ros2/src/drone_mission/test/test_pep257.py`, `project/ros2/src/drone_mission/test/test_xmllint.py`, `project/ros2/src/drone_safety/drone_safety/__init__.py`, `project/ros2/src/drone_safety/drone_safety/arbiter.py`, `project/ros2/src/drone_safety/drone_safety/safety_manager.py`, `project/ros2/src/drone_safety/package.xml`, `project/ros2/src/drone_safety/resource/drone_safety`, `project/ros2/src/drone_safety/setup.cfg`, `project/ros2/src/drone_safety/setup.py`, `project/ros2/src/drone_safety/test/test_arbiter.py`, `project/ros2/src/drone_safety/test/test_flake8.py`, `project/ros2/src/drone_safety/test/test_mypy.py`, `project/ros2/src/drone_safety/test/test_pep257.py`, `project/ros2/src/drone_safety/test/test_xmllint.py`, `project/ros2/src/drone_sim/drone_sim/__init__.py`, `project/ros2/src/drone_sim/drone_sim/estimator.py`, `project/ros2/src/drone_sim/drone_sim/estimator_node.py`, `project/ros2/src/drone_sim/drone_sim/flow_check.py`, `project/ros2/src/drone_sim/drone_sim/flow_model.py`, `project/ros2/src/drone_sim/package.xml`, `project/ros2/src/drone_sim/resource/drone_sim`, `project/ros2/src/drone_sim/setup.cfg`, `project/ros2/src/drone_sim/setup.py`, `project/ros2/src/drone_sim/test/test_estimator.py`, `project/ros2/src/drone_sim/test/test_flake8.py`, `project/ros2/src/drone_sim/test/test_flow_model.py`, `project/ros2/src/drone_sim/test/test_mypy.py`, `project/ros2/src/drone_sim/test/test_pep257.py`, `project/ros2/src/drone_sim/test/test_xmllint.py`, `project/ros2/src/drone_teleop/drone_teleop/__init__.py`, `project/ros2/src/drone_teleop/drone_teleop/radio_teleop.py`, `project/ros2/src/drone_teleop/package.xml`, `project/ros2/src/drone_teleop/resource/drone_teleop`, `project/ros2/src/drone_teleop/setup.cfg`, `project/ros2/src/drone_teleop/setup.py`, `project/ros2/src/drone_teleop/test/test_flake8.py`, `project/ros2/src/drone_teleop/test/test_mypy.py`, `project/ros2/src/drone_teleop/test/test_pep257.py`, `project/ros2/src/drone_teleop/test/test_radio_teleop.py`, `project/ros2/src/drone_teleop/test/test_xmllint.py`, `project/telemetry/inav/msp/captures/flat_still.jsonl`, `project/telemetry/inav/msp/captures/flow_moving.jsonl`, `project/telemetry/inav/msp/captures/radio_off.jsonl`, `project/telemetry/inav/msp/captures/tilted.jsonl`, `project/telemetry/inav/msp/rates/rate_baseline.txt`, `project/telemetry/inav/msp/rates/rate_gap10.txt`, `project/telemetry/inav/msp/rates/rate_nops.txt`, `project/telemetry/inav/msp/rates/rate_t1500.txt`, `project/telemetry/inav/msp/rates/run1.txt`, `project/telemetry/inav/msp/rates/run2.txt`, `project/telemetry/inav/msp/rates/run3.txt`, `project/telemetry/inav_telemetry.py`, `project/telemetry/latency_test.py`, `project/telemetry/msp_inventory.py`, `project/telemetry/receiver_crsf_ping.py`, `project/telemetry/tests/conftest.py`, `project/telemetry/tests/test_capture_copies.py`, `project/telemetry/tests/test_captures.py`, `project/telemetry/tests/test_decoders.py`, `project/telemetry/tests/test_msp_frame.py`
- Other uncommitted files (not code, don't affect the tests): `.claude/hooks/check-test-run.sh`, `.github/workflows/ci.yml`, `.github/workflows/nightly.yml`, `.gitignore`, `Makefile`, `compose.yaml`, `docs/.obsidian/app.json`, `docs/.obsidian/appearance.json`, `docs/.obsidian/core-plugins.json`, `docs/.obsidian/graph.json`, `docs/.obsidian/workspace.json`, `"docs/3D Print Files/box.stl"`, `"docs/3D Print Files/esp12.stl"`, `"docs/3D Print Files/holder.stl"`, `"docs/3D Print Files/pmw3901.stl"`, `"docs/3D Print Files/wanhao_d12_230_fixed.ini"`, `docs/extras/Drone_Betaflight_Backup.txt`, `docs/extras/Drone_INAV_Backup_26_10_26.txt`, `docs/extras/Drone_XYZ_INAV_Calibration.txt`, `docs/extras/ELRS-v4.1.0-betafpv.rx_2400.nano-LBT-bindphrase.bin.gz`, `docs/extras/ESC_configurator_log.txt`, `docs/extras/ESC_settings.png`, `docs/extras/ODDITYRCF7AIO_inav_9.1.0_v2.zip`, `docs/extras/folders-graph.svg`, `docs/extras/receiver_crsf_ping.py`, `docs/extras/wanhao12-230_MOUNT.ini`, `docs/extras/wire_diagram.png`, `roomodel/room.stl`, `seame-docker/.env.example`, `seame-docker/Dockerfile`, `seame-docker/logs/measurements/.gitkeep`, `seame-docker/logs/measurements/measure_wifi_rtt.py`, `seame-docker/ros2_ws/src/drone_basics_cpp/CMakeLists.txt`, `seame-docker/ros2_ws/src/drone_basics_cpp/package.xml`, `seame-docker/ros2_ws/src/drone_basics_cpp/src/watchdog.cpp`, `seame-docker/ros2_ws/src/drone_basics_py/drone_basics_py/__init__.py`, `seame-docker/ros2_ws/src/drone_basics_py/drone_basics_py/py.typed`, `seame-docker/ros2_ws/src/drone_basics_py/drone_basics_py/radio_teleop.py`, `seame-docker/ros2_ws/src/drone_basics_py/drone_basics_py/setpoint_pub.py`, `seame-docker/ros2_ws/src/drone_basics_py/package.xml`, `seame-docker/ros2_ws/src/drone_basics_py/resource/drone_basics_py`, `seame-docker/ros2_ws/src/drone_basics_py/setup.cfg`, `seame-docker/ros2_ws/src/drone_basics_py/setup.py`, `seame-docker/ros2_ws/src/drone_basics_py/test/test_copyright.py`, `seame-docker/ros2_ws/src/drone_basics_py/test/test_flake8.py`, `seame-docker/ros2_ws/src/drone_basics_py/test/test_mypy.py`, `seame-docker/ros2_ws/src/drone_basics_py/test/test_pep257.py`, `seame-docker/ros2_ws/src/drone_basics_py/test/test_radio_teleop.py`, `seame-docker/ros2_ws/src/drone_basics_py/test/test_xmllint.py`, `seame-docker/ros2_ws/src/drone_bringup/CMakeLists.txt`, `seame-docker/ros2_ws/src/drone_bringup/config/basics.yaml`, `seame-docker/ros2_ws/src/drone_bringup/config/gz_bridge.yaml`, `seame-docker/ros2_ws/src/drone_bringup/config/sim.yaml`, `seame-docker/ros2_ws/src/drone_bringup/launch/basics.launch.py`, `seame-docker/ros2_ws/src/drone_bringup/launch/sim.launch.py`, `seame-docker/ros2_ws/src/drone_bringup/models/grass_ground/materials/textures/grass.jpg`, `seame-docker/ros2_ws/src/drone_bringup/models/grass_ground/model.config`, `seame-docker/ros2_ws/src/drone_bringup/models/grass_ground/model.sdf`, `seame-docker/ros2_ws/src/drone_bringup/models/room/meshes/room.stl`, `seame-docker/ros2_ws/src/drone_bringup/models/room/model.config`, `seame-docker/ros2_ws/src/drone_bringup/models/room/model.sdf`, `seame-docker/ros2_ws/src/drone_bringup/package.xml`, `seame-docker/ros2_ws/src/drone_bringup/test/fake_drone.py`, `seame-docker/ros2_ws/src/drone_bringup/test/test_config.py`, `seame-docker/ros2_ws/src/drone_bringup/test/test_launch_files.py`, `seame-docker/ros2_ws/src/drone_bringup/test/test_sim_flight.py`, `seame-docker/ros2_ws/src/drone_bringup/test/test_stack.py`, `seame-docker/ros2_ws/src/drone_bringup/test/test_worlds.py`, `seame-docker/ros2_ws/src/drone_bringup/worlds/outdoor_field.sdf`, `seame-docker/ros2_ws/src/drone_bringup/worlds/room_world.sdf`, `seame-docker/ros2_ws/src/drone_fc_bridge/CMakeLists.txt`, `seame-docker/ros2_ws/src/drone_fc_bridge/package.xml`, `seame-docker/ros2_ws/src/drone_fc_bridge/src/fc_bridge.cpp`, `seame-docker/ros2_ws/src/drone_fc_bridge/src/inav_decode.cpp`, `seame-docker/ros2_ws/src/drone_fc_bridge/src/inav_decode.hpp`, `seame-docker/ros2_ws/src/drone_fc_bridge/src/msp.cpp`, `seame-docker/ros2_ws/src/drone_fc_bridge/src/msp.hpp`, `seame-docker/ros2_ws/src/drone_fc_bridge/test/capture.hpp`, `seame-docker/ros2_ws/src/drone_fc_bridge/test/data/flat_still.jsonl`, `seame-docker/ros2_ws/src/drone_fc_bridge/test/data/flow_moving.jsonl`, `seame-docker/ros2_ws/src/drone_fc_bridge/test/data/radio_off.jsonl`, `seame-docker/ros2_ws/src/drone_fc_bridge/test/data/tilted.jsonl`, `seame-docker/ros2_ws/src/drone_fc_bridge/test/test_failsafes.py`, `seame-docker/ros2_ws/src/drone_fc_bridge/test/test_inav.py`, `seame-docker/ros2_ws/src/drone_fc_bridge/test/test_inav_decode.cpp`, `seame-docker/ros2_ws/src/drone_fc_bridge/test/test_msp.cpp`, `seame-docker/ros2_ws/src/drone_fc_bridge/test/test_services.py`, `seame-docker/ros2_ws/src/drone_fc_bridge/test/test_state.py`, `seame-docker/ros2_ws/src/drone_interfaces/CMakeLists.txt`, `seame-docker/ros2_ws/src/drone_interfaces/action/Goto.action`, `seame-docker/ros2_ws/src/drone_interfaces/action/Land.action`, `seame-docker/ros2_ws/src/drone_interfaces/action/Takeoff.action`, `seame-docker/ros2_ws/src/drone_interfaces/msg/FcStatus.msg`, `seame-docker/ros2_ws/src/drone_interfaces/msg/OpticalFlow.msg`, `seame-docker/ros2_ws/src/drone_interfaces/package.xml`, `seame-docker/ros2_ws/src/drone_mission/drone_mission/__init__.py`, `seame-docker/ros2_ws/src/drone_mission/drone_mission/demo_flight.py`, `seame-docker/ros2_ws/src/drone_mission/drone_mission/logic.py`, `seame-docker/ros2_ws/src/drone_mission/drone_mission/mission.py`, `seame-docker/ros2_ws/src/drone_mission/package.xml`, `seame-docker/ros2_ws/src/drone_mission/resource/drone_mission`, `seame-docker/ros2_ws/src/drone_mission/setup.cfg`, `seame-docker/ros2_ws/src/drone_mission/setup.py`, `seame-docker/ros2_ws/src/drone_mission/test/test_copyright.py`, `seame-docker/ros2_ws/src/drone_mission/test/test_flake8.py`, `seame-docker/ros2_ws/src/drone_mission/test/test_logic.py`, `seame-docker/ros2_ws/src/drone_mission/test/test_mypy.py`, `seame-docker/ros2_ws/src/drone_mission/test/test_pep257.py`, `seame-docker/ros2_ws/src/drone_mission/test/test_xmllint.py`, `seame-docker/ros2_ws/src/drone_safety/drone_safety/__init__.py`, `seame-docker/ros2_ws/src/drone_safety/drone_safety/arbiter.py`, `seame-docker/ros2_ws/src/drone_safety/drone_safety/safety_manager.py`, `seame-docker/ros2_ws/src/drone_safety/package.xml`, `seame-docker/ros2_ws/src/drone_safety/resource/drone_safety`, `seame-docker/ros2_ws/src/drone_safety/setup.cfg`, `seame-docker/ros2_ws/src/drone_safety/setup.py`, `seame-docker/ros2_ws/src/drone_safety/test/test_arbiter.py`, `seame-docker/ros2_ws/src/drone_safety/test/test_copyright.py`, `seame-docker/ros2_ws/src/drone_safety/test/test_flake8.py`, `seame-docker/ros2_ws/src/drone_safety/test/test_mypy.py`, `seame-docker/ros2_ws/src/drone_safety/test/test_pep257.py`, `seame-docker/ros2_ws/src/drone_safety/test/test_xmllint.py`, `seame-docker/ros2_ws/src/drone_sim_sensors/drone_sim_sensors/__init__.py`, `seame-docker/ros2_ws/src/drone_sim_sensors/drone_sim_sensors/estimator.py`, `seame-docker/ros2_ws/src/drone_sim_sensors/drone_sim_sensors/estimator_node.py`, `seame-docker/ros2_ws/src/drone_sim_sensors/drone_sim_sensors/flow_check.py`, `seame-docker/ros2_ws/src/drone_sim_sensors/drone_sim_sensors/flow_model.py`, `seame-docker/ros2_ws/src/drone_sim_sensors/package.xml`, `seame-docker/ros2_ws/src/drone_sim_sensors/resource/drone_sim_sensors`, `seame-docker/ros2_ws/src/drone_sim_sensors/setup.cfg`, `seame-docker/ros2_ws/src/drone_sim_sensors/setup.py`, `seame-docker/ros2_ws/src/drone_sim_sensors/test/test_copyright.py`, `seame-docker/ros2_ws/src/drone_sim_sensors/test/test_estimator.py`, `seame-docker/ros2_ws/src/drone_sim_sensors/test/test_flake8.py`, `seame-docker/ros2_ws/src/drone_sim_sensors/test/test_flow_model.py`, `seame-docker/ros2_ws/src/drone_sim_sensors/test/test_pep257.py`, `seame-docker/ros2_ws/tools/arm_bounce.py`, `seame-docker/ros2_ws/tools/odom_yaw.py`, `seame-docker/scripts/logbook.py`, `seame-docker/scripts/make-env.sh`, `seame-docker/scripts/open_tabs.sh`, `seame-docker/scripts/run_tests.sh`, `seame-docker/scripts/sim_flight_test.sh`, `seame-docker/scripts/sim_joy.sh`, `seame-docker/scripts/sim_keyboard.sh`, `seame-docker/scripts/smoke_test.sh`, `seame-docker/scripts/stop_sim.sh`, `seame-docker/scripts/test_report.py`, `telemetry/inav/captures/inav/msp/captures/flat_still.jsonl`, `telemetry/inav/captures/inav/msp/captures/flow_moving.jsonl`, `telemetry/inav/captures/inav/msp/captures/radio_off.jsonl`, `telemetry/inav/captures/inav/msp/captures/tilted.jsonl`, `telemetry/inav/captures/inav/msp/rates/rate_baseline.txt`, `telemetry/inav/captures/inav/msp/rates/rate_gap10.txt`, `telemetry/inav/captures/inav/msp/rates/rate_nops.txt`, `telemetry/inav/captures/inav/msp/rates/rate_t1500.txt`, `telemetry/inav/captures/inav/msp/rates/run1.txt`, `telemetry/inav/captures/inav/msp/rates/run2.txt`, `telemetry/inav/captures/inav/msp/rates/run3.txt`, `telemetry/inav/captures/msp_inventory.py`, `telemetry/inav_telemetry.py`, `telemetry/latency_test.py`, `telemetry/tests/conftest.py`, `telemetry/tests/test_capture_copies.py`, `telemetry/tests/test_captures.py`, `telemetry/tests/test_decoders.py`, `telemetry/tests/test_msp_frame.py`, `.env.example`, `project/.dockerignore`, `project/Dockerfile`, `project/hardware/3d-print/box.stl`, `project/hardware/3d-print/esp12.stl`, `project/hardware/3d-print/holder.stl`, `project/hardware/3d-print/pmw3901.stl`, `project/hardware/3d-print/wanhao12-230_MOUNT.ini`, `project/hardware/3d-print/wanhao_d12_230_fixed.ini`, `project/hardware/esc/ESC_configurator_log.txt`, `project/hardware/esc/ESC_settings.png`, `project/hardware/flight-controller/Drone_Betaflight_Backup.txt`, `project/hardware/flight-controller/Drone_INAV_Backup_26_10_26.txt`, `project/hardware/flight-controller/Drone_XYZ_INAV_Calibration.txt`, `project/hardware/flight-controller/ODDITYRCF7AIO_inav_9.1.0_v2.zip`, `project/hardware/radio/ELRS-v4.1.0-betafpv.rx_2400.nano-LBT-bindphrase.bin.gz`, `project/hardware/wiring/wire_diagram.png`, `project/scripts/logbook.py`, `project/scripts/make-env.sh`, `project/scripts/measure_wifi_rtt.py`, `project/scripts/open_tabs.sh`, `project/scripts/ros2_tools/arm_bounce.py`, `project/scripts/ros2_tools/odom_yaw.py`, `project/scripts/run_tests.sh`, `project/scripts/sim_flight_test.sh`, `project/scripts/sim_joy.sh`, `project/scripts/sim_keyboard.sh`, `project/scripts/stop_sim.sh`, `project/scripts/test_report.py`
- **Environment:** ROS jazzy, Ubuntu 24.04.5 LTS, Python 3.12.3, dev container; clean build, the same commands as CI
- **Build:** exit 0, 21 s. **ROS tests:** exit 0, 107 s. **Telemetry tests:** exit 0, 0 s

## Result

| | Test cases | Passed | Skipped | Failed |
| --- | --- | --- | --- | --- |
| Behaviour tests | 362 | 362 | 0 | 0 |
| Lint and style checks | 26 | 26 | 0 | 0 |
| **Total** | 388 | 388 | 0 | 0 |

colcon's own summary counts 402 "tests": the 388 test cases plus 14 CTest entries (one per C++ test file or linter), which wrap cases already counted.

## Compared with the previous run

Previous: `2026-11-18_5957765-dirty` (`5957765`): 388 cases, 0 failed. Now: 388 cases, 0 failed.

Same tests, same results.

## By package

| Package | Behaviour | Lint | Passed | Skipped | Failed | Time |
| --- | --- | --- | --- | --- | --- | --- |
| `drone_bringup` | 63 | 10 | 73 | 0 | 0 | 67.0 s |
| `drone_fc_bridge` | 60 | 0 | 60 | 0 | 0 | 38.6 s |
| `drone_mission` | 44 | 4 | 48 | 0 | 0 | 5.1 s |
| `drone_safety` | 9 | 4 | 13 | 0 | 0 | 4.91 s |
| `drone_sim` | 22 | 4 | 26 | 0 | 0 | 5.28 s |
| `drone_teleop` | 24 | 4 | 28 | 0 | 0 | 5.58 s |
| `telemetry` | 140 | 0 | 140 | 0 | 0 | 0 s |

## Every test

### `drone_bringup` · `flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `flake8` | pass | 0.000 |  |

### `drone_bringup` · `lint_cmake` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `CMakeLists.txt` | pass | 0.000 |  |

### `drone_bringup` · `pep257` (7)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `./launch/sim.launch.py` | pass | 0.000 |  |
| `./test/fake_drone.py` | pass | 0.000 |  |
| `./test/test_config.py` | pass | 0.000 |  |
| `./test/test_launch_files.py` | pass | 0.000 |  |
| `./test/test_sim_flight.py` | pass | 0.000 |  |
| `./test/test_stack.py` | pass | 0.000 |  |
| `./test/test_worlds.py` | pass | 0.000 |  |

### `drone_bringup` · `test_config` (15)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mission_climb_speed_equals_fc_limit` | pass | 0.004 |  |
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
| `test_every_section_is_a_launched_node` | pass | 0.000 |  |

### `drone_bringup` · `test_launch_files` (22)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_default_is_the_sim_with_the_radio_and_the_mission` | pass | 0.014 |  |
| `test_inav_backend_starts_no_gazebo_and_no_radio_nodes` | pass | 0.002 |  |
| `test_with_the_radio_only_the_radio_arms` | pass | 0.005 |  |
| `test_without_the_radio_the_mission_arms` | pass | 0.003 |  |
| `test_demo_flight_only_with_demo` | pass | 0.007 |  |
| `test_nothing_flies_without_a_source[source:=none demo:=false]` | pass | 0.003 |  |
| `test_nothing_flies_without_a_source[source:=none demo:=true]` | pass | 0.003 |  |
| `test_gazebo_gets_the_world_and_headless_adds_server_only` | pass | 0.007 |  |
| `test_each_source_publishes_on_its_own_topic` | pass | 0.004 |  |
| `test_sim_time_only_in_the_sim` | pass | 0.066 |  |
| `test_every_node_reads_sim_yaml` | pass | 0.065 |  |
| `test_our_programs_are_installed` | pass | 0.066 |  |
| `test_other_programs_are_installed` | pass | 0.065 |  |
| `test_parameter_files_are_installed` | pass | 0.066 |  |
| `test_every_package_it_starts_is_a_dependency` | pass | 0.074 |  |
| `test_every_package_it_starts_is_checked_first` | pass | 0.066 |  |
| `test_a_missing_package_stops_the_launch[drone_mission]` | pass | 0.001 |  |
| `test_a_missing_package_stops_the_launch[drone_fc_bridge]` | pass | 0.001 |  |
| `test_a_missing_package_stops_the_launch[ros_gz_bridge]` | pass | 0.001 |  |
| `test_a_missing_package_stops_the_launch[joy]` | pass | 0.001 |  |
| `test_the_real_drone_needs_none_of_the_sim_packages` | pass | 0.002 |  |
| `test_refuses_to_start_next_to_a_running_sim` | pass | 0.002 |  |

### `drone_bringup` · `test_stack` (5)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_disarm_mid_flight` | pass | 8.807 |  |
| `test_disarm_while_the_radio_flies` | pass | 7.790 |  |
| `test_full_flight` | pass | 26.536 |  |
| `test_radio_takes_over_and_gives_back` | pass | 18.254 |  |
| `test_takeoff_refused_until_armed` | pass | 1.283 |  |

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
| `test_drone_fuel_model_is_pinned[multicopter_velocity_control.sdf]` | pass | 0.001 |  |
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
| `EveryGoodFrameParses` | pass | 0.006 |  |
| `DamagedFramesAreNotReturned` | pass | 0.003 |  |
| `WholeFileAsOneStream` | pass | 0.016 |  |
| `RecoversFrameEmbeddedInDamagedOne` | pass | 0.005 |  |
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
| `DrainsABigBacklogInLinearTime` | pass | 0.066 |  |
| `FeedAfterPartialDrainKeepsOrder` | pass | 0.000 |  |

### `drone_fc_bridge` · `test_failsafes` (9)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_fresh_setpoint_is_forwarded` | pass | 1.810 |  |
| `test_horizontal_clamp_keeps_direction` | pass | 1.811 |  |
| `test_inf_is_rejected` | pass | 1.810 |  |
| `test_nan_is_rejected_and_times_out` | pass | 2.319 |  |
| `test_roll_and_pitch_rates_are_zeroed` | pass | 1.811 |  |
| `test_sim_enable_is_published` | pass | 2.310 |  |
| `test_timeout_sends_zero` | pass | 2.821 |  |
| `test_vertical_and_yaw_clamp` | pass | 2.819 |  |
| `test_zero_without_setpoints` | pass | 1.810 |  |

### `drone_fc_bridge` · `test_inav` (3)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_arm_is_refused` | pass | 0.003 |  |
| `test_nothing_reaches_the_sim` | pass | 0.000 |  |
| `test_status_says_inav_and_disarmed` | pass | 0.000 |  |

### `drone_fc_bridge` · `test_services` (4)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_disarm_and_rearm` | pass | 3.021 |  |
| `test_hold_sends_zero_despite_setpoints` | pass | 1.529 |  |
| `test_starts_armed` | pass | 0.000 |  |
| `test_status_reports_setpoint_age` | pass | 1.450 |  |

### `drone_fc_bridge` · `test_state` (7)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_body_velocity_rotated_by_heading` | pass | 1.514 |  |
| `test_height_and_orientation_from_sim` | pass | 0.407 |  |
| `test_position_is_integrated_not_copied` | pass | 1.521 |  |
| `test_range_level` | pass | 0.410 |  |
| `test_range_out_of_range_is_inf` | pass | 1.231 |  |
| `test_range_reads_longer_when_tilted` | pass | 0.409 |  |
| `test_velocity_passes_through` | pass | 0.605 |  |

### `drone_mission` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.168 |  |

### `drone_mission` · `test_logic` (44)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_starts_grounded_and_silent` | pass | 0.001 |  |
| `test_takeoff_hold_land` | pass | 0.001 |  |
| `test_takeoff_to_a_given_height` | pass | 0.001 |  |
| `test_takeoff_refused_without_range` | pass | 0.001 |  |
| `test_takeoff_refused_above_range_max` | pass | 0.000 |  |
| `test_takeoff_refused_in_the_air` | pass | 0.001 |  |
| `test_takeoff_timeout_lands` | pass | 0.001 |  |
| `test_cancel_takeoff_holds_where_it_is` | pass | 0.001 |  |
| `test_goto_forward` | pass | 0.001 |  |
| `test_goto_is_relative_to_heading` | pass | 0.001 |  |
| `test_goto_square_comes_back` | pass | 0.003 |  |
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
| `test_mypy` | pass | 3.106 |  |

### `drone_mission` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.060 |  |

### `drone_mission` · `test_xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_xmllint` | pass | 0.205 |  |

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

### `drone_safety` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.086 |  |

### `drone_safety` · `test_mypy` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mypy` | pass | 3.016 |  |

### `drone_safety` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.017 |  |

### `drone_safety` · `test_xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_xmllint` | pass | 0.396 |  |

### `drone_sim` · `test_estimator` (11)

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

### `drone_sim` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.124 |  |

### `drone_sim` · `test_flow_model` (11)

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

### `drone_sim` · `test_mypy` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mypy` | pass | 3.096 |  |

### `drone_sim` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.031 |  |

### `drone_sim` · `test_xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_xmllint` | pass | 0.206 |  |

### `drone_teleop` · `test_flake8` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_flake8` | pass | 0.147 |  |

### `drone_teleop` · `test_mypy` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_mypy` | pass | 2.951 |  |

### `drone_teleop` · `test_pep257` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_pep257` | pass | 0.028 |  |

### `drone_teleop` · `test_radio_teleop` (24)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_switch_off_publishes_nothing` | pass | 0.070 |  |
| `test_engage_after_hold` | pass | 0.035 |  |
| `test_no_engage_before_hold` | pass | 0.008 |  |
| `test_bounce_while_arming_does_not_engage` | pass | 0.007 |  |
| `test_engages_once_bounce_settles` | pass | 0.008 |  |
| `test_off_is_immediate` | pass | 0.009 |  |
| `test_bounce_while_disarming_does_not_reengage` | pass | 0.009 |  |
| `test_engage_refused_with_throttle_off_centre` | pass | 0.008 |  |
| `test_throttle_moves_freely_once_engaged` | pass | 0.008 |  |
| `test_sticks_scaled_to_limits` | pass | 0.008 |  |
| `test_deadband_gives_zero` | pass | 0.008 |  |
| `test_reengage_needs_throttle_centred_again` | pass | 0.008 |  |
| `test_switch_at_threshold_is_off` | pass | 0.007 |  |
| `test_missing_arm_axis_is_off` | pass | 0.007 |  |
| `test_arm_switch_arms_the_fc_once` | pass | 0.008 |  |
| `test_arm_switch_off_disarms_even_in_flight` | pass | 0.008 |  |
| `test_arm_switch_on_at_start_must_be_cycled` | pass | 0.007 |  |
| `test_arming_refused_with_throttle_off_centre` | pass | 0.007 |  |
| `test_arm_alone_does_not_take_over` | pass | 0.007 |  |
| `test_takeover_alone_does_nothing` | pass | 0.007 |  |
| `test_takeover_with_arm_on_engages_after_hold` | pass | 0.008 |  |
| `test_takeover_off_releases_at_once` | pass | 0.011 |  |
| `test_arm_off_releases_even_with_takeover_on` | pass | 0.008 |  |
| `test_missing_takeover_axis_is_off` | pass | 0.008 |  |

### `drone_teleop` · `test_xmllint` (1)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_xmllint` | pass | 0.204 |  |

### `telemetry` · `test_capture_copies` (2)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_recordings_are_where_this_test_looks` | pass | 0.000 |  |
| `test_copies_in_ros2_match_the_recordings` | pass | 0.001 |  |

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
| `test_every_good_reply_is_whole_with_a_valid_crc[flat_still]` | pass | 0.004 |  |
| `test_every_good_reply_is_whole_with_a_valid_crc[tilted]` | pass | 0.003 |  |
| `test_every_good_reply_is_whole_with_a_valid_crc[radio_off]` | pass | 0.003 |  |
| `test_every_good_reply_is_whole_with_a_valid_crc[flow_moving]` | pass | 0.004 |  |
| `test_parser_reads_every_good_reply[flat_still]` | pass | 0.004 |  |
| `test_parser_reads_every_good_reply[tilted]` | pass | 0.004 |  |
| `test_parser_reads_every_good_reply[radio_off]` | pass | 0.004 |  |
| `test_parser_reads_every_good_reply[flow_moving]` | pass | 0.004 |  |
| `test_parser_rejects_every_damaged_reply[flat_still]` | pass | 0.001 |  |
| `test_parser_rejects_every_damaged_reply[tilted]` | pass | 0.001 |  |
| `test_parser_rejects_every_damaged_reply[radio_off]` | pass | 0.001 |  |
| `test_parser_rejects_every_damaged_reply[flow_moving]` | pass | 0.001 |  |
| `test_every_good_reply_decodes_fully[flat_still]` | pass | 0.001 |  |
| `test_every_good_reply_decodes_fully[tilted]` | pass | 0.001 |  |
| `test_every_good_reply_decodes_fully[radio_off]` | pass | 0.001 |  |
| `test_every_good_reply_decodes_fully[flow_moving]` | pass | 0.001 |  |
| `test_flat_still_is_level` | pass | 0.001 |  |
| `test_tilted_rolls_about_46_degrees[tilted]` | pass | 0.003 |  |
| `test_radio_off_is_failsafe[radio_off]` | pass | 0.002 |  |
| `test_flow_moving_sees_motion` | pass | 0.001 |  |
| `test_still_states_have_little_flow[flat_still]` | pass | 0.001 |  |
| `test_still_states_have_little_flow[tilted]` | pass | 0.001 |  |
| `test_still_states_have_little_flow[radio_off]` | pass | 0.001 |  |
| `test_identity[flat_still]` | pass | 0.002 |  |
| `test_identity[tilted]` | pass | 0.002 |  |
| `test_identity[radio_off]` | pass | 0.002 |  |
| `test_identity[flow_moving]` | pass | 0.002 |  |
| `test_mode_names[flat_still]` | pass | 0.001 |  |
| `test_mode_names[tilted]` | pass | 0.001 |  |
| `test_mode_names[radio_off]` | pass | 0.001 |  |
| `test_mode_names[flow_moving]` | pass | 0.001 |  |
| `test_disarmed_on_the_bench_without_a_rangefinder[flat_still]` | pass | 0.002 |  |
| `test_disarmed_on_the_bench_without_a_rangefinder[tilted]` | pass | 0.002 |  |
| `test_disarmed_on_the_bench_without_a_rangefinder[radio_off]` | pass | 0.002 |  |
| `test_disarmed_on_the_bench_without_a_rangefinder[flow_moving]` | pass | 0.002 |  |
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
| `test_short_or_odd_payload_only_raises_what_poll_catches[inav_status]` | pass | 0.001 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[inav_analog]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[opflow]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[rangefinder]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[local_pose]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[nav_status]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[link_stats]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[api_version]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[fc_variant]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[fc_version]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[board_info]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[craft_name]` | pass | 0.000 |  |
| `test_short_or_odd_payload_only_raises_what_poll_catches[mode_names]` | pass | 0.000 |  |
| `test_command_numbers` | pass | 0.000 |  |
| `test_raw_payload_is_hex_in_json_and_decimal_on_screen` | pass | 0.000 |  |

### `telemetry` · `test_msp_frame` (32)

| Test | Result | Time (s) | Note |
| --- | --- | --- | --- |
| `test_crc_standard_check_value` | pass | 0.000 |  |
| `test_crc_of_nothing_is_zero` | pass | 0.000 |  |
| `test_crc_matches_real_drone_frames[24583e0001000300000205a6]` | pass | 0.000 |  |
| `test_crc_matches_real_drone_frames[24583e0002000400494e415694]` | pass | 0.000 |  |
| `test_crc_matches_real_drone_frames[24583e006c000600f7ffc0ff300089]` | pass | 0.000 |  |
| `test_crc_matches_real_drone_frames[24583e0000201600ff013200a3000d00000002041000000200000000000007]` | pass | 0.000 |  |
| `test_crc_matches_real_drone_frames[24583e00022018004050063e00e90300000c000000cf0000000000000052000072]` | pass | 0.000 |  |
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
| `test_bad_crc_is_dropped_and_the_next_frame_still_parses` | pass | 0.000 |  |
| `test_error_reply_is_reported_not_ok` | pass | 0.000 |  |
| `test_own_request_echoed_back_is_ignored` | pass | 0.000 |  |
| `test_impossible_size_is_skipped` | pass | 0.000 |  |
| `test_incomplete_frame_waits_for_the_rest` | pass | 0.000 |  |
| `test_marker_split_across_two_reads` | pass | 0.000 |  |
| `test_valid_reply_inside_a_corrupt_one_is_recovered` | pass | 0.000 |  |
| `test_request_sends_the_frame_and_returns_the_payload` | pass | 0.000 |  |
| `test_reply_split_over_several_reads` | pass | 0.000 |  |
| `test_stale_reply_to_another_command_is_skipped` | pass | 0.000 |  |
| `test_error_reply_returns_not_ok` | pass | 0.000 |  |
| `test_no_reply_times_out` | pass | 0.203 |  |
| `test_closed_connection_raises` | pass | 0.001 |  |

## Warnings in the output

Lines mentioning a warning (node log lines at WARN level left out: those are the behaviour under test):

```text
../project/telemetry/tests/test_decoders.py::test_every_battery_state[1-warning] PASSED [ 40%]
Warning: This process (pid=9387) is multi-threaded, use of fork() may lead to deadlocks in the child.
Warning: This process (pid=9450) is multi-threaded, use of fork() may lead to deadlocks in the child.
```

## Console summary lines

Packages are tested in parallel, so these lines interleave.

```text
Finished <<< drone_interfaces [0.29s]
============================== 13 passed in 3.59s ==============================
============================== 48 passed in 3.69s ==============================
======================= 28 passed, 32 warnings in 3.92s ========================
======================= 26 passed, 32 warnings in 3.72s ========================
Finished <<< drone_safety [4.91s]
Finished <<< drone_mission [5.10s]
Finished <<< drone_sim [5.28s]
Finished <<< drone_teleop [5.58s]
100% tests passed, 0 tests failed out of 6
Finished <<< drone_fc_bridge [38.6s]
100% tests passed, 0 tests failed out of 8
Summary: 7 packages finished [1min 46s]
Summary: 262 tests, 0 errors, 0 failures, 0 skipped
```

Full output: `console.log.gz` (`zcat console.log.gz | less`). Every test case, with any failure message: `results.json`.
