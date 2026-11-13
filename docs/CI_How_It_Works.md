---
title: How the CI tests work
---
# How the CI tests work

How every automated test in this repo is found, run and judged: on GitHub (CI), every night (Gazebo flight), and on your laptop. The **telemetry tests** (the MSP link to INAV) get the most detail, in [section 4](#4-telemetry-tests-job-telemetry-python).

State of `main` on **2026-11-13** (commit `9cb07e9`). Counts were taken from real runs that day: `colcon test` in the dev container (HEAD, clean build in `/tmp`) and `pytest telemetry` (Python 3.12).

> This page replaces the root `TESTS.md`, which was deleted in `a9425e4`. Its useful parts (the bug history, how to run each kind of test, how to add one) are carried over and brought up to date. [docs/TESTS.md](./TESTS.md) is still the page for checks done **by hand** (hardware, Wi-Fi link, sim flights watched by a person) and their last results. [docs/CI_Tests.md](./CI_Tests.md) is the older **plan** (test IDs A1–E11); its IDs are reused here.

## Contents

1. [The picture in one minute](#1-the-picture-in-one-minute)
2. [Status today](#2-status-today)
3. [How CI finds and runs the tests](#3-how-ci-finds-and-runs-the-tests)
4. [Telemetry tests (job `telemetry-python`)](#4-telemetry-tests-job-telemetry-python)
5. [ROS tests (job `ros2-build-test`)](#5-ros-tests-job-ros2-build-test)
6. [Docker image (job `docker-image`)](#6-docker-image-job-docker-image)
7. [Keeping red PRs out (job `block-red-pr`)](#7-keeping-red-prs-out-job-block-red-pr)
8. [Flight in Gazebo (workflow `nightly.yml`)](#8-flight-in-gazebo-workflow-nightlyyml)
9. [Running the tests yourself](#9-running-the-tests-yourself)
10. [Reading a failure](#10-reading-a-failure)
11. [How to add a test](#11-how-to-add-a-test)
12. [Bugs the tests have found](#12-bugs-the-tests-have-found)
13. [What isn't tested yet, in priority order](#13-what-isnt-tested-yet-in-priority-order)
14. [Questions to settle](#14-questions-to-settle)
15. [Words used on this page](#15-words-used-on-this-page)

---

## 1. The picture in one minute

```
 git push / pull request ──► .github/workflows/ci.yml  (every push and PR to main, test, ci/**, Develop)
                               ├─ ros2-build-test   clean ros:jazzy container: rosdep → colcon build → colcon test
                               ├─ telemetry-python  Python 3.12: py_compile → flake8 → pytest telemetry
                               ├─ docker-image      the dev container's Dockerfile still builds
                               └─ block-red-pr      any of the 3 failed on a PR → PR back to draft + comment

 02:00 UTC every night ─────► .github/workflows/nightly.yml  (also: Actions button, PRs that touch the sim)
                               └─ gazebo-flight     dev image → scripts/sim_flight_test.sh → Gazebo, headless,
                                                    one real flight checked against ground truth

 your laptop ───────────────► seame-docker/scripts/run_tests.sh   same commands as ros2-build-test,
                                                                  result kept in seame-docker/logs/tests/
```

| Workflow · job | Runs on | Tests | Takes | Blocks a PR? |
| --- | --- | --- | --- | --- |
| `ci.yml` · `ros2-build-test` | push, PR, button | 259 cases: 226 behaviour + 33 lint | about 3 min (tests about 105 s) | Yes, through `block-red-pr` |
| `ci.yml` · `telemetry-python` | push, PR, button | 140 cases + syntax + flake8 | about 15 s | Yes, through `block-red-pr` |
| `ci.yml` · `docker-image` | push, PR, button | the image builds | seconds from cache, minutes cold | Yes, through `block-red-pr` |
| `ci.yml` · `block-red-pr` | PRs only, when a job above failed | none: it acts | seconds | It is the blocker |
| `nightly.yml` · `gazebo-flight` | 02:00 UTC, button, PRs touching the sim | 8 flight steps | 4–5 min with the image | No |

**Layers of testing.** The tests go from fast and narrow to slow and close to reality. Each layer catches what the one before can't:

| Layer | What runs | Example | Where |
| --- | --- | --- | --- |
| 1. Files, without running anything | YAML, launch files, SDF worlds read as data | `test_config.py`: the mission's climb speed equals fc_bridge's limit | every push |
| 2. Pure logic, no ROS | a class fed numbers | `test_logic.py`: a whole mission flown against a toy drone in milliseconds | every push |
| 3. Real recordings | bytes recorded from the real drone | `test_captures.py`: every MSP reply the drone sent, through the real parser | every push |
| 4. One real node | the compiled program, a test node plays everyone else | `test_failsafes.py`: fc_bridge sends zero 0.3 s after the last setpoint | every push |
| 5. The whole stack, fake drone | mission + safety_manager + fc_bridge + flow_model + estimator | `test_stack.py`: takeoff, goto, radio takeover, kill switch | every push |
| 6. Gazebo physics | the real launch file, the real simulator | `test_sim_flight.py`: takeoff, hover, a square, land, mission killed mid-flight | nightly |
| 7. The real drone | hardware on the bench | arming, failsafe, Wi-Fi round trip | by hand, see [docs/TESTS.md](./TESTS.md) |

---

## 2. Status today

| What | Result on 2026-11-13 | Notes |
| --- | --- | --- |
| `colcon test`, HEAD `9cb07e9`, dev container | **259 cases: 254 passed, 5 skipped, 0 failed** (colcon prints "277 tests": it also counts 18 CTest wrappers) | The 5 skips are on purpose: 4 copyright checks (no license headers yet) and cppcheck on `watchdog.cpp` (too slow in cppcheck 2.13) |
| `pytest telemetry` | **140 cases pass** (139 + 1 skipped when run from a copy outside the repo) | flake8 clean |
| Last run kept in `logs/tests/` | `2026-11-13_32cfee3`: **FAILED, 4 tests** | Fixed since. Commit `c727000` made the new estimator `fc/odom`'s publisher (`publish_odom: false` in `sim.yaml`). `test_stack.py` started neither the estimator nor `flow_model`, and `fake_drone.py` didn't publish the `/sim/ground_truth` that `flow_model` reads, so the mission had no odometry (3 failures). `test_launch_files.py` didn't expect the new node (1 failure). Fixed by `7325660`, `f9d11ea`, `38c4384` and `f4e9ef2`. **No run has been kept for HEAD yet**: run `./scripts/run_tests.sh` and commit the folder |
| GitHub Actions | not checked from here (the `gh` CLI isn't logged in on this machine) | Look at the repo's **Actions** tab. Check that `nightly.yml` has run since it reached `main` |

**Counts by file** (behaviour tests; lint in [section 5.7](#57-lint-and-style-33-cases)):

| Package | File | Cases | Kind |
| --- | --- | --- | --- |
| telemetry (not ROS) | `test_msp_frame.py` | 32 | pytest, framing |
| | `test_decoders.py` | 59 | pytest, decoders |
| | `test_captures.py` | 47 | pytest, real drone recordings |
| | `test_capture_copies.py` | 2 | pytest, the C++ copies match |
| `drone_fc_bridge` | `test_failsafes.py` | 9 | launch test |
| | `test_state.py` | 7 | launch test |
| | `test_services.py` | 4 | launch test |
| | `test_inav.py` | 3 | launch test |
| | `test_msp.cpp` | 21 | GoogleTest (C++) |
| | `test_inav_decode.cpp` | 16 | GoogleTest (C++) |
| `drone_bringup` | `test_config.py` | 17 | pytest, reads `sim.yaml` |
| | `test_launch_files.py` | 24 | pytest, inspects `sim.launch.py` |
| | `test_worlds.py` | 21 | pytest, reads the SDF worlds |
| | `test_stack.py` (+ `fake_drone.py`) | 5 | launch test, whole stack |
| | `test_sim_flight.py` | 8 steps | launch test, Gazebo, **nightly only** |
| `drone_mission` | `test_logic.py` | 44 | pytest, no ROS |
| `drone_safety` | `test_arbiter.py` | 9 | pytest, no ROS |
| `drone_basics_py` | `test_radio_teleop.py` | 24 | pytest, node without launch |
| `drone_sim_sensors` | `test_flow_model.py` | 11 | pytest, no ROS |
| | `test_estimator.py` | 11 | pytest, no ROS |

---

## 3. How CI finds and runs the tests

### 3.1 The workflow files

GitHub runs every file in [.github/workflows/](../.github/workflows/) as its own workflow, started by that file's `on:` section. The two files don't call each other.

**[ci.yml](../.github/workflows/ci.yml)**
- **Triggers:** push and pull request to `main`, `Develop`, `test` and any `ci/**` branch, plus the "Run workflow" button (`workflow_dispatch`). `Develop` was deleted on Nov 12 but is still listed (harmless). **`staging` and feature branches are not listed**, so a push there runs nothing until a PR targets one of the branches above.
- **`concurrency: ci-<branch>`, `cancel-in-progress: true`:** a new push cancels the run still going on the same branch.
- **`permissions: contents: read`:** jobs can read the repo and nothing else. Only `block-red-pr` gets `pull-requests: write`.

**[nightly.yml](../.github/workflows/nightly.yml)**
- **Triggers:** `cron: '0 2 * * *'` (02:00 UTC), the button, and PRs that change `drone_bringup/launch/**`, `drone_bringup/config/**`, `test_sim_flight.py`, `sim_flight_test.sh` or `nightly.yml` itself. The cron and the button only work for a workflow file that is on the default branch (`main`). It is there now.

### 3.2 How each kind of test is found

| Where the test lives | How it is found | So, to add one |
| --- | --- | --- |
| **Python ROS package** (`drone_mission`, `drone_safety`, `drone_basics_py`, `drone_sim_sensors`) | `colcon test` runs pytest on the package's `test/` folder; every `test_*.py` is picked up | Drop `test/test_<x>.py` in the package |
| **CMake ROS package** (`drone_fc_bridge`, `drone_bringup`, `drone_basics_cpp`) | Only what `CMakeLists.txt` registers: `add_launch_test(...)` (starts nodes), `ament_add_pytest_test(...)` (plain pytest), `ament_add_gtest(...)` (C++). `ament_lint_auto_find_test_dependencies()` adds the linters named in `package.xml` | Register it in `CMakeLists.txt` and add its `<test_depend>`s to `package.xml` |
| **`telemetry/`** (plain Python, not a ROS package) | colcon never sees it. The `telemetry-python` job runs `pytest telemetry` | Drop `telemetry/tests/test_<x>.py` |
| **`test_sim_flight.py`** | Deliberately **not** registered with colcon (too slow for every push). Only `scripts/sim_flight_test.sh` runs it, and the nightly runs that script. Its lint still runs on every push | Add a step to it |

### 3.3 Why CI skips a few tests the dev container runs

`ros2-build-test` installs dependencies with:

```bash
rosdep install --from-paths src --ignore-src -y --rosdistro jazzy \
  --dependency-types build --dependency-types buildtool \
  --dependency-types build_export --dependency-types test
```

Run-time-only packages (`exec_depend`) are left out on purpose: that skips Gazebo (`ros_gz_sim`, `ros_gz_bridge`) and `joy`, which makes the job much faster. Tests that need them skip themselves when they're missing: the checks on Gazebo's own default world `multicopter_velocity_control.sdf` in `test_worlds.py` (the file ships with Gazebo), and `test_other_programs_are_installed` in `test_launch_files.py`. The dev container has everything, so `run_tests.sh` runs them. That's why the dev container skips 5 and CI skips a few more.

### 3.4 Keeping test runs apart from a sim that's running

Launch tests start real ROS nodes, so they could hear a sim running on the same machine, or a teammate's laptop on the lab Wi-Fi (team domain 6). Each one gets its own domain and stays on localhost:

| Tests | Isolation | Set in |
| --- | --- | --- |
| fc_bridge launch tests | `ROS_DOMAIN_ID=199`, `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` | `drone_fc_bridge/CMakeLists.txt` |
| `test_stack.py` | `ROS_DOMAIN_ID=198`, localhost | `drone_bringup/CMakeLists.txt` |
| `test_sim_flight.py` | `ROS_DOMAIN_ID=196`, localhost, `GZ_PARTITION=flight_test` (its own Gazebo channel) | `scripts/sim_flight_test.sh` |

So you can keep your own sim open while tests run.

---

## 4. Telemetry tests (job `telemetry-python`)

### 4.1 What is being tested, and why it matters

"Telemetry" here means **talking to the real flight controller**. The drone runs INAV, which only answers when asked: the ground computer sends an MSP request and INAV sends one reply. The path is:

```
 ground computer ──Wi-Fi──► ESP-12 (esp-link, TCP port 23) ──UART1, 115200 baud──► OddityRC F7 (INAV 9.1.x)
   inav_telemetry.py                passes bytes through unchanged                  answers each MSP request
   fc_bridge (later, C++)  ◄────────────────────── the reply comes back the same way ◄──────┘
```

Two programs speak this protocol:
- **[telemetry/inav_telemetry.py](../telemetry/inav_telemetry.py)** (Python, standard library only): the tool the team uses today to read the drone. It polls 13 live messages (attitude, altitude, IMU, RC channels, motors, status, battery, optical flow, rangefinder, local pose, nav status, link stats) and prints them, or logs JSON lines. **This is what the `telemetry-python` job tests.**
- **`fc_msp`** (C++, [drone_fc_bridge/src/msp.cpp](../seame-docker/ros2_ws/src/drone_fc_bridge/src/msp.cpp) and [inav_decode.cpp](../seame-docker/ros2_ws/src/drone_fc_bridge/src/inav_decode.cpp)): the same protocol for fc_bridge's future `inav` backend. Built and tested, **not yet linked into fc_bridge**. Its tests run in the ROS job ([section 4.8](#48-the-c-twin-fc_msp-tested-in-the-ros-job)).

Both read the **same four recordings** of the real drone. A unit or byte-order mistake in this layer doesn't crash anything. It just shows wrong numbers (a roll 10× too big, metres read as centimetres, a negative current read as 42 949 kW), and someone trusts them. That's why every unit is pinned to a known value here.

### 4.2 MSP v2 in five lines, with a real frame

```
'$' 'X' dir | flag | cmd (u16, little-endian) | size (u16, LE) | payload (size bytes) | crc
dir: '<' request, '>' reply, '!' error reply ("I don't know this command")
crc: CRC-8/DVB-S2 (polynomial 0xD5) over flag, cmd, size and payload; not over '$', 'X', dir
```

A real `MSP_ATTITUDE` reply from the drone lying flat (`flat_still.jsonl`), byte by byte:

```
24 58 3e | 00   | 6c 00     | 06 00  | f7 ff   c0 ff   30 00 | 89
 $  X  > | flag | cmd = 108 | size 6 | roll    pitch   yaw   | crc
                                     | 0xfff7  0xffc0  0x0030
                                     | = −9    = −64   = 48
                                     | −0.9°   −6.4°   48°     (roll, pitch in 0.1°; yaw in 1°)
```

That's exactly what the tests check: the CRC matches (`0x89`), the signed 16-bit reading gives −9 and not 65 527, and the scaling gives −0.9° and not −9°. For the full protocol see [Msp_primer.md](./Msp_primer.md). For every message's layout see [telemetry/candidatesList.md](../telemetry/candidatesList.md).

### 4.3 What the job does, step by step

From [ci.yml](../.github/workflows/ci.yml), on `ubuntu-24.04` with Python 3.12:

| Step | Command | What it proves | Guard |
| --- | --- | --- | --- |
| Check out | `actions/checkout@v4` | the whole repo is there, so `test_capture_copies.py` can also see `seame-docker/ros2_ws` | |
| Python | `actions/setup-python@v5`, 3.12 | the same Python as the dev container (3.12.3) | |
| Syntax check | `python -m py_compile telemetry/*.py` | the **top-level** scripts parse: `inav_telemetry.py`, `latency_test.py`. The glob isn't recursive; `msp_inventory.py` is covered by flake8 below | skipped if `telemetry/*.py` is empty |
| Lint | `pip install flake8` → `flake8 telemetry --max-line-length=140` | every `.py` under `telemetry/` (scripts, tests, `inav/captures/msp_inventory.py`): undefined names, unused imports, style | same |
| Unit tests | `pip install pytest` → `python -m pytest telemetry -v` | the 140 cases below | skipped if `telemetry/tests/*.py` is empty |

**No drone, no network, no ROS.** Every test feeds bytes in and checks what comes out.

### 4.4 `conftest.py`: shared setup

[telemetry/tests/conftest.py](../telemetry/tests/conftest.py):
- puts `telemetry/` on `sys.path`, so tests can `import inav_telemetry`;
- `reply(hex)`: turns a recorded reply frame (hex text) into `(cmd, payload)`, after checking it starts with `$X>` and its length matches its size field.

### 4.5 `test_msp_frame.py`: framing (32 cases)

**How.** Two techniques:
- the reply parser `MSPClient._next_frame()` gets a byte buffer directly (`frames_in(data)` returns every frame it finds, in order);
- `MSPClient.request()` talks to a **`FakeSocket`**: `recv()` hands out chosen chunks of bytes, then raises `socket.timeout` like the real 50 ms socket; `sendall()` records what was sent. The client is built with `MSPClient.__new__` so no real connection is opened.

Six real frames from the drone are used: API version, FC variant, attitude, `MSP2_INAV_STATUS`, `MSP2_INAV_ANALOG`, and optical flow while moving. There's also a damaged `MSP_BOXNAMES` reply recorded in `radio_off.jsonl` that has a complete, valid `MSP_ALTITUDE` reply inside it.

| Group | Tests | What it proves |
| --- | --- | --- |
| Checksum | `test_crc_standard_check_value` (CRC of `"123456789"` is `0xBC`, the published check value), `test_crc_of_nothing_is_zero`, `test_crc_matches_real_drone_frames` (×6), `test_crc_detects_a_single_flipped_bit` | the CRC is the real CRC-8/DVB-S2, not just self-consistent |
| Requests | `test_request_frame_layout`, `test_request_frame_with_payload`, `test_v2_command_ids_are_two_bytes_little_endian` (×3: 1, 0x2000, 0x2001…), `test_request_matches_the_reply_header` | commands above 255 (all of INAV's own) are encoded right; otherwise INAV answers the wrong message or nothing |
| Parser | `test_parses_a_real_reply`, `test_back_to_back_replies_come_out_in_order`, `test_garbage_before_a_frame_is_skipped`, `test_bad_crc_is_dropped_and_the_next_frame_still_parses`, `test_error_reply_is_reported_not_ok`, `test_own_request_echoed_back_is_ignored`, `test_impossible_size_is_skipped`, `test_incomplete_frame_waits_for_the_rest`, `test_marker_split_across_two_reads` | the parser never loses its place in a noisy stream |
| Recovery | `test_valid_reply_inside_a_corrupt_one_is_recovered` | a good reply hidden inside a damaged one is found ([bug 1](#12-bugs-the-tests-have-found)) |
| `request()` | `test_request_sends_the_frame_and_returns_the_payload`, `test_reply_split_over_several_reads`, `test_stale_reply_to_another_command_is_skipped`, `test_error_reply_returns_not_ok`, `test_no_reply_times_out` (returns in 0.2–0.5 s), `test_closed_connection_raises` | late replies aren't matched to the wrong request; a silent drone doesn't hang the program |

**Catches:** a broken checksum (every reply looks damaged, or damaged ones get through); wrong byte order; a parser that loses its place after noise or across TCP reads; a reply matched to the wrong request; hanging forever when the drone goes quiet. These are exactly the situations a Wi-Fi link produces in flight, and they're hard to reproduce by hand.

### 4.6 `test_decoders.py`: decoders (59 cases)

**How.** Three kinds of input:
1. **Hand-built payloads** (`struct.pack` with chosen values), to pin each unit;
2. **real payloads from the drone**, checked against what the drone was doing;
3. **fixed bugs**, at the end of the file, where fc_bridge's C++ decoders (written from the INAV 9.1.0 source) showed this script was wrong.

The `drone_modes` fixture loads the drone's own `MSP_BOXNAMES` reply into `MODE_NAMES`, as the program does at start-up. INAV's mode bitmask means "the n-th name in that list is active", not a fixed ID.

| Group | Examples | Pins down |
| --- | --- | --- |
| Units and scaling | `test_attitude_tenths_of_a_degree`, `test_altitude_cm_to_m`, `test_raw_imu_axis_order`, `test_opflow_signed_rates`, `test_msp_analog_scaling`, `test_inav_analog_scaling_and_flags`, `test_every_battery_state` (×4), `test_rangefinder_cm_to_m`, `test_rangefinder_minus_one_is_out_of_range`, `test_raw_gps_degrees_and_optional_hdop`, `test_comp_gps` | ×10 and ×100 errors, swapped axes, sign errors |
| Lists and text | `test_u16_list_ignores_a_trailing_odd_byte`, `test_text_strips_padding`, `test_box_names_split` | RC channels and motor lists; mode names |
| Bit fields | `test_sensor_bits`, `test_armed_bit_is_not_a_blocker`, `test_arming_blockers_named_in_bit_order`, `test_flight_modes_from_names`, `test_flight_mode_without_a_name` | a field shifted by one bit names the wrong mode or blocker |
| Status messages | `test_inav_status_fields`, `test_inav_status_without_mixer_profile`, `test_status_and_status_ex` | every field of `MSP2_INAV_STATUS`, and the older replies |
| Real drone data | `test_identity` (INAV 9.1.0, API 2.5), `test_drone_mode_names`, `test_real_attitude` (×3: flat, tilted 46°, radio off), `test_real_imu_agrees_with_the_tilt`, `test_real_status_flat`, `test_real_status_tilted_is_not_level`, `test_real_battery` (16.16 V), `test_real_optical_flow_while_moving` (quality 92, 46 °/s), `test_real_rc_and_motors` | the decoders agree with the physical state of the drone |
| Robustness | `test_short_or_odd_payload_only_raises_what_poll_catches` (×19, every decoder) | a short reply may only raise `struct.error` or `IndexError`, the two errors `poll()` catches; anything else would crash the telemetry loop |
| Command numbers | `test_command_numbers` | each entry asks INAV 9.1.0 for the right message |
| Output | `test_raw_payload_is_hex_in_json_and_decimal_on_screen` | undecoded bytes print correctly |
| Fixed bugs | `test_only_real_arming_blockers_are_listed`, `test_rangefinder_zero_is_not_a_distance`, `test_inav_analog_negative_power_and_drawn` | [bugs 5, 6, 7](#12-bugs-the-tests-have-found) stay fixed |

### 4.7 `test_captures.py`: replaying the real drone (47 cases)

**The data.** [telemetry/inav/captures/inav/msp/captures/](../telemetry/inav/captures/inav/msp/captures/) holds four JSON Lines files, recorded on 2026-11-09 with `msp_inventory.py capture` (issue #125): OddityRC F7, INAV 9.1.0, esp-link 3.2.47, props off, receiver **not bound**. About 20 replies per message per file. Line 1 is the setup; every other line is one request:

```json
{"name": "MSP_ATTITUDE", "cmd": 108, "i": 0, "ok": true, "rtt_ms": 26.1, "hex": "24583e006c0006…"}
```

`ok: false` means the reply came back damaged (bad CRC, cut short). `"error": "timeout"` means no reply (no `hex`). About 19–24 % of requests timed out during capture.

| Recording | The drone was… | What the tests expect |
| --- | --- | --- |
| `flat_still` | level on two books, still | roll −2…0°, pitch −7…−5°, heading 48/49°, gravity on Z (acc Z > 450) |
| `tilted` | one side raised | roll 44–48°, gravity split evenly between Y and Z, "not level" blocks arming |
| `radio_off` | level, radio off | FAILSAFE is the only mode, "rc_link" blocks arming, throttle channel at its failsafe value 885 |
| `flow_moving` | slid by hand over a pattern | flow reaches ≥ 40 °/s (about 56), quality drops to 0 at least once and is 100 most of the time |

**How.** `good(state, name)` returns the payload (bytes `[8:-1]` of the frame) of every undamaged reply to one message. Most tests run once per recording (`parametrize` over the 4 states).

| Group | Tests | Cases |
| --- | --- | --- |
| The recordings themselves | `test_recording_header`, `test_timeouts_have_no_frame` | 8 |
| Every frame | `test_every_good_reply_is_whole_with_a_valid_crc`, `test_parser_reads_every_good_reply`, `test_parser_rejects_every_damaged_reply`, `test_every_good_reply_decodes_fully` (never falls back to raw bytes) | 16 |
| One per state | `test_flat_still_is_level`, `test_tilted_rolls_about_46_degrees`, `test_radio_off_is_failsafe`, `test_flow_moving_sees_motion`, `test_still_states_have_little_flow` (×3, < 25 °/s) | 7 |
| Same in all four | `test_identity` (INAV 9.1.0, API 2.5), `test_mode_names` (ARM at 0, FAILSAFE at 17), `test_disarmed_on_the_bench_without_a_rangefinder` (sensors exactly acc, baro, opflow, temp; 4 motors at 1000), `test_battery` (16.0–16.4 V, 4 cells, "ok") | 16 |

**Why it's the strongest telemetry test:** hundreds of real frames, including the damage the real Wi-Fi link produces, through the exact code path. A decoder change that only breaks some real messages fails here.

**Limits:** bench recordings only. No radio bound, no rangefinder fitted, no flight, so these values are never seen moving: altitude, local pose, link stats, RC sticks. New recordings are needed once those exist ([section 13](#13-what-isnt-tested-yet-in-priority-order)).

### 4.8 `test_capture_copies.py`: both test suites read the same data (2 cases)

fc_bridge's C++ tests read **copies** of the four recordings in [drone_fc_bridge/test/data/](../seame-docker/ros2_ws/src/drone_fc_bridge/test/data/), because only `ros2_ws` is mounted in the dev container. If someone re-records and forgets to copy, the Python and C++ tests quietly test different data.

- `test_recordings_are_where_this_test_looks`: the four originals exist (otherwise the next check would skip without anyone noticing).
- `test_copies_in_ros2_ws_match_the_recordings`: every file under `seame-docker/ros2_ws/src` with a recording's name is byte-identical to the original. On failure it prints the `cp` command that fixes it. It skips when `telemetry/` was copied outside the repo (no `ros2_ws` next to it).

### 4.9 The C++ twin: `fc_msp`, tested in the ROS job

Not part of `telemetry-python`, but it's the same protocol and the same recordings. It's the code that will read the real drone from ROS. GoogleTest, registered with `ament_add_gtest` in [drone_fc_bridge/CMakeLists.txt](../seame-docker/ros2_ws/src/drone_fc_bridge/CMakeLists.txt). [capture.hpp](../seame-docker/ros2_ws/src/drone_fc_bridge/test/capture.hpp) reads the `.jsonl` copies.

**`test_msp.cpp` (21 cases):** standard CRC check value and captured CRCs; `SameBytesAsPython` (requests byte-identical to `inav_telemetry.py`); `OnlyReadCommands` (**only the nine read commands can be built; `MSP_SET_RAW_RC` and every other command are refused**, so this library can't fly the drone by mistake); payload limits; every good captured frame parses and damaged ones never come out; each whole file as one stream; `RecoversFrameEmbeddedInDamagedOne`; garbage, split-at-every-byte, echoed requests, error frames, bad CRC; `OversizedSizeDoesNotStall`; bounded buffer; `SkipPendingReleasesTheRepliesBehindIt` (give up on a broken header at the reply timeout); a 2 MB backlog drains in linear time.

**`test_inav_decode.cpp` (16 cases):** API version, variant, version; rangefinder from captures and its states (−1 out of range, 0 and other negatives "no reading"); attitude and its limits; status in every capture plus a hand-built armed one; optical flow (captured and hand-built negatives); battery (captured, and hand-built with negative current and power); local pose (hand-built, to pin field order and signs). Every decoder refuses a payload that's too short and accepts a longer one (newer firmware appends fields).

**Python and C++, side by side:**

| | `inav_telemetry.py` | `fc_msp` (C++) |
| --- | --- | --- |
| Used by | people, on a laptop, today | fc_bridge `inav` backend, once ROS-6 step B links it |
| Units | degrees, m, V (readable) | SI: rad, m, m/s, V, A, W |
| Commands it can send | any it's given | only 9 read commands; writes refused |
| Largest reply accepted | 4096 bytes | 512 (INAV's reply buffer) |
| Broken header | drops the `$X`, searches again | same, plus `skip_pending()` at the reply timeout |
| Optical flow sign | reads int16 | reads int16, with a warning: in the captures **no flow rate is ever negative**, even with the gyro swinging both ways. INAV 9.1.0 may send negatives as 0 ([question 5](#14-questions-to-settle)) |

### 4.10 What the telemetry tests don't cover

| Gap | Risk | Next step (plan ID) |
| --- | --- | --- |
| The poll loop (`poll()`, `run()`): rejected messages dropped, JSON per cycle, `--log` | a change breaks the program while every decoder still passes | A4: fake client with canned replies |
| **Default port**: `inav_telemetry.py` and `latency_test.py` default to `--port 5760`, the old MicroPython bridge. esp-link listens on **23** (the Nov 12 measurements used `--port 23`) | the tools "don't connect" with default arguments | change the defaults, or document `--port 23` (decide first which bridge is current, [question 1](#14-questions-to-settle)) |
| `latency_test.py` and `msp_inventory.py` have their **own copies** of the CRC and request builder | a fix in one copy doesn't reach the others | move them into one shared module, or test all copies give identical bytes |
| Real firmware behaviour after an INAV upgrade | a removed or changed message | A5: INAV SITL nightly |
| The live link (latency, loss) | the control loop is planned around numbers nobody re-checks | manual: `latency_test.py`, `measure_wifi_rtt.py` (see [docs/TESTS.md](./TESTS.md)) |
| Radio bound, rangefinder fitted, flying | decoders never see those values move | new recordings with `msp_inventory.py capture` |

### 4.11 Running them locally

The host's Python may lack pytest (this machine has Python 3.8 without it). Two options:

```bash
# A. on the host, repo root, with pytest installed (pip install pytest flake8)
python3 -m pytest telemetry -v                       # 140 passed
flake8 telemetry --max-line-length=140

# B. in the dev container (telemetry/ isn't mounted there, so copy it in)
docker exec seame-dev rm -rf /tmp/tele               # otherwise docker cp nests it
docker cp telemetry seame-dev:/tmp/tele
docker exec -w /tmp seame-dev python3 -m pytest tele -v                               # 139 passed, 1 skipped
docker exec -w /tmp seame-dev python3 -m flake8 --select=E,W,F --max-line-length=140 tele
```

In option B the skip is `test_copies_in_ros2_ws_match_the_recordings`: there's no `ros2_ws` next to `/tmp/tele`. `--select=E,W,F` makes the container's flake8 (which has extra plugins) behave like CI's plain flake8.

---

## 5. ROS tests (job `ros2-build-test`)

### 5.1 What the job does

On `ubuntu-24.04`, inside the official `ros:jazzy` image (not our dev image), working directory `seame-docker/ros2_ws`:

1. `apt-get update`, `rosdep update`, then `rosdep install` with build, buildtool, build_export and test dependencies only ([section 3.3](#33-why-ci-skips-a-few-tests-the-dev-container-runs)).
2. `colcon build --event-handlers console_direct+` (a normal build, not `--symlink-install`).
3. `colcon test`, then `colcon test-result --verbose`. **`test-result` is what fails the job**: it exits non-zero when any test failed.
4. Always (even on failure): uploads `build/*/test_results` as the **`ros2-test-results`** artifact (the XML reports).

Building in a clean image is the point: it proves every dependency is declared in a `package.xml`. Something that only works because your container happens to have a package installed fails here.

### 5.2 Layer 1: files, checked without running them (`drone_bringup`, 62 cases)

**[test_config.py](../seame-docker/ros2_ws/src/drone_bringup/test/test_config.py) (17):** loads `config/sim.yaml` and checks that the limits agree across nodes. A limit raised in one place but not the other makes the drone behave differently from what the mission expects, silently.
- mission's `max_vz` = fc_bridge's `max_speed_z`; safety_manager's `source_timeout_s` = fc_bridge's `setpoint_timeout_s`;
- each command speed (mission, radio) ≤ fc_bridge's clamp, otherwise fc_bridge clamps it silently (parametrized);
- `range_min < ground_h < target_h < range_max`; the demo height fits the rangefinder; optical flow works once airborne (`flow_model.min_height` vs `mission.ground_h`);
- the radio is first in `priority`;
- every time and rate is > 0; decimals are written as floats (`2.0`, not `2`: ROS rejects an int for a double parameter);
- every section name is a node the launch starts (a typo would make the node ignore its whole section).

**[test_launch_files.py](../seame-docker/ros2_ws/src/drone_bringup/test/test_launch_files.py) (24):** builds `sim.launch.py`'s description for argument combinations **without starting anything** (about 1 s) and inspects which nodes, parameters and remaps it would start.
- Default = sim + radio + mission + `flow_model` + `estimator`; `backend:=inav` starts no Gazebo, no bridge and no radio nodes; with the radio only the radio arms, without it the mission arms; `demo_flight` only with `demo:=true`; the circle demo starts `setpoint_pub` after the rest; nothing flies without a source; `headless:=true` adds `-s` (server only); each source on its own topic (`/cmd/mission`, `/cmd/radio`); `use_sim_time` only in the sim; every node gets `sim.yaml`.
- Every program it starts is installed (ours, and others such as `joy_node`); parameter files are installed; every package is a dependency of `drone_bringup` and is checked before anything starts; a missing package stops the launch; the real drone needs none of the sim packages; it refuses to start next to a sim already running in your `GZ_PARTITION`.
- **Catches:** a renamed executable or a wrong path. Before this test, that only showed up when someone launched the sim. It also fails whenever the launch starts a new node, until its expected list is updated (as with the estimator on Nov 13), so a change to what flies is always a deliberate one.

**[test_worlds.py](../seame-docker/ros2_ws/src/drone_bringup/test/test_worlds.py) (21):** reads every SDF world as XML (no Gazebo): `outdoor_field.sdf`, `room_world.sdf` and Gazebo's default world (6 checks each), plus 3 general checks.
- the physics system is loaded; exactly one model has a velocity controller on the topics `gz_bridge.yaml` sends to (`/X3/gazebo/command/twist`, `/X3/enable`); it publishes odometry where `gz_bridge.yaml` reads; it starts on the ground; its Fuel model is pinned to a version; every `model://` it uses exists;
- the bridge talks to one drone; every model in `drone_bringup/models/` has its files (textures, meshes); worlds and models are installed.
- **Catches:** a new world where the drone ignores commands, has no odometry, or misses a texture.

### 5.3 Layer 2: logic, without launching anything (99 cases)

These test the "brains" as plain Python classes (`radio_teleop` is the exception: its node is created, but fed `Joy` messages by direct calls). Each node is split into a logic file (tested here) and a thin ROS wrapper, so whole flights run in milliseconds with no timing flakiness.

**[test_logic.py](../seame-docker/ros2_ws/src/drone_mission/test/test_logic.py) (44):** the mission state machine (`logic.py`) against a toy drone (height follows commanded vertical speed, rangefinder 0.04–4.0 m, optional sag and ceiling). Groups: **takeoff** (to 1.2 m ± 5 cm; refused without range, above range max, in the air, until range is steady for 1 s; timeout lands; cancel holds); **goto** (relative to heading; a square comes back within 20 cm; refused on the ground or without odometry; aborts when odometry stops; timeout; feedback); **land and hold** (preempts goto, can't be cancelled, hold corrects sag, tilt correction, `-inf` = ground); **rangefinder loss** (hover then resume, abort goto, land blind after `lost_hold_s`, never climbs without a goal); **radio override** (goal aborts and mission goes quiet, goals refused, control back holds where the pilot left it); **arming** (takeoff refused until armed or before any status, stale "disarmed" status ignored, disarm in the air grounds it).

**[test_arbiter.py](../seame-docker/ros2_ws/src/drone_safety/test/test_arbiter.py) (9):** who commands the drone. Radio > manual > mission, 0.3 s freshness: nothing active at start; one source forwarded; radio takes over and the mission is dropped; manual beats mission but not radio; control returns 0.3 s after the radio goes quiet; unknown sources never forwarded; a change reported once; a clock going backwards (sim reset) isn't "fresh".

**[test_radio_teleop.py](../seame-docker/ros2_ws/src/drone_basics_py/test/test_radio_teleop.py) (24):** feeds fake `Joy` messages to `radio_teleop.on_joy` and records what it would publish and call. Arm switch: holds 0.1 s before counting (the Pocket's switch bounces up to 35 ms, recorded with `tools/arm_bounce.py`); off is immediate, even in flight (kill switch); on at start must be cycled; refused with the throttle off centre. Takeover switch: arm alone or takeover alone flies nothing; both on engages after the hold. Sticks scaled to 0.5 / 0.3 / 1.0, deadband, frame `base_link`.

**[test_flow_model.py](../seame-docker/ros2_ws/src/drone_sim_sensors/test/test_flow_model.py) (11):** the simulated optical flow. Hover gives no flow; forward gives negative flow Y and left gives positive flow X (the sign convention); rotating in place equals the body rate; tilt lengthens the distance; unusable geometry gives nothing; whole degrees truncated toward zero (as INAV's MSP sends); quality 0 below 8 cm or above 7 rad/s; noise has the requested spread.

**[test_estimator.py](../seame-docker/ros2_ws/src/drone_sim_sensors/test/test_estimator.py) (11, new Nov 13):** estimator v1, which now produces `fc/odom` in the sim. Forward and left flow give forward and left velocity; rotating in place gives no velocity; yaw turns body forward into world left; position is integrated; height corrected for tilt; too close reads as the ground; out of range keeps the last height; lost flow holds the speed briefly (0.3 s) then assumes stopped; vertical speed follows a climb and stays calm in a noisy hover.

### 5.4 Layer 4: fc_bridge alone (`drone_fc_bridge`, 23 launch cases)

fc_bridge is the last software step before the motors. Each file starts the **real compiled fc_bridge** alone, on the wall clock, without Gazebo; a test node plays both the commander and Gazebo.

| File | Cases | Checks |
| --- | --- | --- |
| [test_failsafes.py](../seame-docker/ros2_ws/src/drone_fc_bridge/test/test_failsafes.py) | 9 | zero with no setpoints (still publishes every tick); fresh setpoint forwarded unchanged; zero after 0.3 s (not before); NaN rejected and times out; infinity rejected; horizontal clamp keeps direction ((3, 4) → (0.3, 0.4)); z ±0.3 and yaw ±1.0 clamped; roll and pitch rates zeroed; `/X3/enable` published |
| [test_state.py](../seame-docker/ros2_ws/src/drone_fc_bridge/test/test_state.py) | 7 | noise 0, fake `/X3/odom` in: velocity passes through; position is **integrated, never copied** from Gazebo; body velocity rotated by heading; height and attitude from the sim; range = z level, 2z at 60° roll; ±inf out of range |
| [test_services.py](../seame-docker/ros2_ws/src/drone_fc_bridge/test/test_services.py) | 4 | starts armed; `fc/arm` false/true toggles `/X3/enable` and `fc/status`; `fc/hold` sends zero despite setpoints; `fc/status` reports the setpoint age |
| [test_inav.py](../seame-docker/ros2_ws/src/drone_fc_bridge/test/test_inav.py) | 3 | `backend:=inav`: status says `inav` and disarmed; `fc/arm` refused both ways ("arming is on the radio"); no publisher on any Gazebo topic |

**Note:** these use fc_bridge's **code defaults** (rangefinder 0.04–4.0 m, VL53L1X-like), while the sim flies with `sim.yaml` (MTF-02P, 0.02–6.0 m, `publish_odom: false`). So the configuration that actually flies is only covered by `test_stack.py` and the nightly (plan B2).

### 5.5 C++ unit tests (`drone_fc_bridge`, 37 cases)

`test_msp.cpp` (21) and `test_inav_decode.cpp` (16): see [section 4.9](#49-the-c-twin-fc_msp-tested-in-the-ros-job).

### 5.6 Layer 5: the whole stack with a fake drone (`test_stack.py`, 5 cases)

[test_stack.py](../seame-docker/ros2_ws/src/drone_bringup/test/test_stack.py) starts the real nodes exactly as `sim.launch.py` does, with `sim.yaml`, on the wall clock. [fake_drone.py](../seame-docker/ros2_ws/src/drone_bringup/test/fake_drone.py) replaces Gazebo, in its own process.

```
 test: Takeoff/Goto/Land ──► mission ──/cmd/mission──► safety_manager ──/fc/setpoint_velocity──► fc_bridge
 test: radio sticks ────────────────────/cmd/radio──────────┘                                     │
 test: fc/arm (kill switch) ─────────────────────────────────────────────────────────────────────► │
                                                                         /X3/gazebo/command/twist ▼ /X3/enable
                                                                                             fake_drone (50 Hz)
            ┌──────────── /X3/odom ◄────────────────────────────────────────────────────────────┤
            │             /sim/ground_truth ◄───────────────────────────────────────────────────┘
            ▼                  ▼
        fc_bridge          flow_model ──fc/optical_flow──► estimator ──fc/odom──► mission
   fc/range, fc/attitude, fc/status ──────────────────────────┴──────────────────► mission
```

fake_drone flies at whatever velocity fc_bridge commands; disarmed in the air, it drops; on its legs it rests at 0.05 m. The test reads `/X3/odom` (the true pose) to check where the drone really went.

| Test | Checks |
| --- | --- |
| `test_takeoff_refused_until_armed` | only the radio arms: Takeoff refused, drone stays on the ground |
| `test_full_flight` | Takeoff reaches `target_h`; 1 m forward really moves about 1 m; turn 90° left, then forward goes to the old left (body to world); asking 2 m/s still arrives; Land; no command ever exceeded the `sim.yaml` limits |
| `test_radio_takes_over_and_gives_back` | radio mid-Goto: Goto aborted ("overridden"), mission silent, new goals refused, drone follows the sticks; sticks quiet: mission holds where the radio left it, then lands |
| `test_disarm_mid_flight` | kill switch mid-Goto: aborted ("disarmed"), the drone drops, the mission goes silent, Takeoff refused |
| `test_disarm_while_the_radio_flies` | kill switch under the radio: once control returns, the mission stays grounded instead of holding (and climbing when re-armed) |

**Catches** what no single-node test can: wrong topic names or remaps, QoS mismatches, wrong frames, a broken radio/mission handover, limits that differ between nodes, and **a node the stack needs but the test doesn't start** (Nov 13: the estimator). It takes about a minute and needs no Gazebo, so it runs on every push. It was flaky until Nov 12 ([bugs 3 and 8](#12-bugs-the-tests-have-found)); since then it passed 6 runs out of 6.

### 5.7 Lint and style (33 cases)

They read code without running it. They come from the ROS package templates (`test_flake8.py` and others in Python packages) and from `ament_lint_auto` (CMake packages).

| Check | Looks at | Packages |
| --- | --- | --- |
| flake8 | Python style and simple bugs (unused imports, undefined names, line length 99, import order) | all Python packages; drone_bringup's launch and test files |
| pep257 | docstrings | same (8 files in drone_bringup) |
| mypy | types | drone_basics_py, drone_mission, drone_safety (**not** drone_sim_sensors) |
| xmllint | `package.xml` against the schema | Python packages except drone_sim_sensors, drone_bringup, drone_basics_cpp |
| lint_cmake, uncrustify | CMake and C++ formatting | drone_bringup (CMake), drone_basics_cpp |
| cppcheck | C++ static analysis | drone_basics_cpp: **skipped** (cppcheck 2.13 too slow) |
| copyright | license headers | **skipped** in 4 Python packages; turned off in CMake packages |

**Gap:** `drone_fc_bridge` has **no lint at all** (its `CMakeLists.txt` doesn't call `ament_lint_auto`), though it holds the most safety-critical C++ (five files). Measured on Nov 12: uncrustify wants about 42 lines reformatted (automatic with `ament_uncrustify --reformat`), plus two small cpplint fixes. No C++ static analysis runs anywhere.

---

## 6. Docker image (job `docker-image`)

Builds [seame-docker/Dockerfile](../seame-docker/Dockerfile) from scratch with Buildx, **without pushing it anywhere**, using GitHub's layer cache (`cache-from/cache-to: type=gha`).

- **Proves:** a new laptop can still build the team's environment (STK-2). It catches an apt package renamed or removed upstream, and a broken `RUN` line, before someone finds out on setup day.
- **Side effect:** its cache is reused by the nightly, which loads the same image in 1–2 minutes.
- **Doesn't prove:** that the image runs Gazebo with a GPU, or that `compose.yaml` works (device mounts, groups). Those are checked by hand ([seame-docker/GUIDE.md](../seame-docker/GUIDE.md)).

## 7. Keeping red PRs out (job `block-red-pr`)

```yaml
needs: [ros2-build-test, telemetry-python, docker-image]
if: failure() && github.event_name == 'pull_request'
```

When any of the three jobs fails on a pull request, it runs `gh pr ready <PR> --undo` (back to **draft**) and comments with a link to the failed run: *"CI failed, so this PR was moved back to draft. Fix the errors, push, wait for green CI, then click 'Ready for review'."*

**Limit:** a draft can still be marked ready by hand and merged. The real lock is GitHub **branch protection with required status checks** on `main` (plan E9, a settings change, needs an admin). Not set up as far as the repo shows.

---

## 8. Flight in Gazebo (workflow `nightly.yml`)

### 8.1 How it runs

1. Build the dev image `seame/ros2-dev:jazzy` from the `docker-image` job's cache (`load: true`), so the sim on GitHub is the sim on our laptops.
2. Run [scripts/sim_flight_test.sh](../seame-docker/scripts/sim_flight_test.sh) `"$RUNNER_TEMP/sim_flight"`. The script:
   - starts a **throwaway container** from the image, no display and no GPU (like GitHub's machines), with `ros2_ws/src` mounted read-only;
   - copies the sources to `/tmp/ws`, runs `colcon build --packages-up-to drone_bringup`;
   - sets `ROS_DOMAIN_ID=196`, localhost only, `GZ_PARTITION=flight_test`;
   - starts `ros2 bag record` of the key topics (`/sim/ground_truth`, `/fc/status`, `/fc/range`, `/fc/odom`, `/cmd/mission`, `/cmd/manual`, `/fc/setpoint_velocity`, `/X3/gazebo/command/twist`, `/safety/active_source`);
   - runs `launch_test test_sim_flight.py --junit-xml flight.xml`, which includes `sim.launch.py headless:=true radio:=false` (Gazebo server only; with no radio the mission arms on Takeoff and disarms after Land);
   - stops the recorder with SIGTERM (a backgrounded job ignores SIGINT), copies every node's log, prints what each step measured and the verdict.
3. Upload the folder as the **`sim-flight`** artifact for 14 days: `flight.log`, `flight.xml`, `flight_bag/` (replay with `ros2 bag play flight_bag`), `ros_log/`, `build.log`.

### 8.2 The eight steps

One flight, in order; after a failed step the rest are skipped (they share the flight). Every check uses **Gazebo's ground truth** (`/sim/ground_truth`), not the drone's own estimate. Tolerances come from `sim.yaml`, so they follow the config.

| Step | Checks | Pass if | Last measured |
| --- | --- | --- | --- |
| `test_1_sim_comes_up` | ground truth, `fc/status`, `fc/range`, action servers, sim time | all within 180 s (the first run downloads the X3 from Fuel); backend `sim` | about 3 s |
| `test_2_on_the_ground_at_start` | on the ground, still, upright | height and `fc/range` < `ground_h` | z 0.054 m |
| `test_3_takeoff` | Takeoff to `target_h` | succeeds; true height and range 1.2 ± 0.1 m | 1.16–1.19 m |
| `test_4_hover_drift` | 3 s to settle, then 10 s hover | no overshoot above 1.3 m; drift < 0.1 m; height 1.2 ± 0.05 m | drift 0.000 m |
| `test_5_square` | 1 m forward + quarter turn left, ×4 | sides 1 ± (`pos_tolerance` + 0.1) m; turns 90° ± (`yaw_tolerance` + 0.02); closes < 0.3 m | sides 0.87–0.98 m, closes < 0.1 m |
| `test_6_speed_capped_at_the_limit` | a Goto asking 2 m/s, every speed since takeoff | > 80 % of `max_speed_xy`, never > limit + 10 %; same for z and yaw | 0.459 m/s, z 0.300 m/s |
| `test_7_land` | Land | succeeds; on the ground; upright; mission disarms | z 0.055 m |
| `test_8_mission_dies_and_the_drone_stops` | SIGKILL the mission mid-Goto, land by hand on `cmd/manual` | stopped (< 0.05 m/s) within `setpoint_timeout_s` + 1 s; coasts < 0.5 m; holds height; lands | about 1 s, 0.23 m |

"Last measured" values are from runs on Nov 12, before the estimator replaced fc_bridge's `fc/odom` on Nov 13. **Rerun it** (`./scripts/sim_flight_test.sh`): the drone now steers on optical-flow odometry, so the square's numbers may change.

**Catches** what the faster layers can't: the launch file, the bridge and Gazebo not working together; real dynamics (overshoot, braking, drift); speeds over the limits in actual flight; a drone that keeps flying when the mission crashes.

**Why not on every push:** it builds an image, starts Gazebo and flies about 2 minutes. It isn't part of `block-red-pr`, so nobody is stopped by it. That also means **somebody has to look at it**: GitHub emails a failed scheduled run only to whoever created the workflow or last changed its cron schedule.

---

## 9. Running the tests yourself

All ROS commands run **inside the dev container** (`cd seame-docker && docker compose exec dev bash`), from `~/ros2_ws`, after `source /opt/ros/jazzy/setup.bash`.

| I want to… | Command | Time |
| --- | --- | --- |
| Run everything the way CI does, and keep the result | host, in `seame-docker/`: `./scripts/run_tests.sh` | about 2 min |
| Quick check while working | `colcon build && colcon test --packages-select <pkg> && colcon test-result --verbose` | depends |
| One pytest file (no build needed) | `python3 -m pytest src/drone_bringup/test/test_config.py -v` | < 1 s |
| Files that read installed things | `source install/setup.bash`, then `python3 -m pytest src/drone_bringup/test/test_launch_files.py src/drone_bringup/test/test_worlds.py -v -rs` | about 1 s |
| Mission logic | `cd src/drone_mission && python3 -m pytest test/test_logic.py -v` | < 1 s |
| C++ tests | `colcon test --packages-select drone_fc_bridge --ctest-args -R 'test_msp\|test_inav_decode'` or `./build/drone_fc_bridge/test_msp --gtest_filter='Parser.*'` | < 1 s |
| One launch test | `export ROS_DOMAIN_ID=198 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST && launch_test src/drone_bringup/test/test_stack.py` | about 60 s |
| Telemetry | [section 4.11](#411-running-them-locally) | < 1 s |
| Gazebo flight | host, in `seame-docker/`: `./scripts/sim_flight_test.sh` (a fresh container; your own sim can stay open) | about 2 min |
| Watch the Gazebo flight | `export ROS_DOMAIN_ID=196 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST GZ_PARTITION=flight_test && launch_test src/drone_bringup/test/test_sim_flight.py`, then in a second terminal `GZ_PARTITION=flight_test gz sim -g` | about 2 min |

**`run_tests.sh` in detail.** It does a clean build and `colcon test` in `/tmp/seame_tests` **inside the container**, so your own `build/` and `install/` are never touched. It copies back the console log and every result file (pytest XML, xUnit, CTest), then [scripts/test_report.py](../seame-docker/scripts/test_report.py) writes `seame-docker/logs/tests/<date>_<commit>[-dirty]/` containing `report.md` (verdict, failures, what changed since the last run), `results.json`, `meta.json`, `console.log.gz`, plus one line in `logs/tests/history.csv`. `-dirty` means uncommitted code under `ros2_ws/` was part of the run. It doesn't run the telemetry tests or the Gazebo flight.

**The commit guard.** [.claude/hooks/check-test-run.sh](../.claude/hooks/check-test-run.sh) is a Claude Code hook. When Claude is about to `git commit` code under `seame-docker/ros2_ws/` and no `logs/tests/<run>/report.md` is part of the commit, it stops the commit and asks you whether to run `run_tests.sh` first. Skip it on purpose with `TESTS_SKIPPED=1 git commit …`. It only affects commits made through Claude, not your own terminal.

**After a `git pull`**: `docker compose down/up` does **not** rebuild the workspace. The workspace is a host folder mounted into the container, and the container runs `sleep infinity`. Run `colcon build --symlink-install` yourself whenever a pull adds an executable to a `setup.py`, a package, a launch file, or changes C++. Otherwise `ros2 launch` fails with "executable '…' not found" (this happened with `estimator` on Nov 13). Python edits to existing files are live with `--symlink-install`.

---

## 10. Reading a failure

| Where it failed | Look at | Typical causes |
| --- | --- | --- |
| `ros2-build-test`, step **Install** | the rosdep output | a `package.xml` names a package that doesn't exist for Jazzy |
| `ros2-build-test`, step **Build** | the first `error:` in the log | C++ compile error; a Python package's `setup.py` broken |
| `ros2-build-test`, step **Test** | the end of the step: `colcon test-result --verbose` lists every failing case with its message. The **`ros2-test-results`** artifact has the XML | a real regression; a missing `<test_depend>` (works locally, fails in the clean image); lint |
| `telemetry-python` | the step that's red: **Syntax** (a file doesn't parse), **Lint** (flake8 lists file:line:code), **Unit tests** (pytest prints the assertion with both values) | a decoder change; a new line > 140 chars |
| `docker-image` | the failing `RUN` line | apt package renamed upstream |
| `gazebo-flight` | the **`sim-flight`** artifact: `flight.log` (which step, measured vs expected), `ros_log/` (each node), `flight_bag/` (replay the flight) | timing in the sim; a launch or config change; Fuel download failed (first run) |
| Locally, `run_tests.sh` | `logs/tests/<run>/report.md`, section **Failures**, then `zcat console.log.gz \| less` | as above |

A launch test that failed **once** and passed on rerun is not "fine". `test_stack.py`'s flakiness on Nov 12 was a real bug (the mission's commands stalling for 0.8 s, [bug 3](#12-bugs-the-tests-have-found)).

---

## 11. How to add a test

- **Python ROS package:** add `test/test_<x>.py`. Found automatically; flake8, pep257 (and mypy where enabled) apply to it.
- **CMake package** (`drone_bringup`, `drone_fc_bridge`): add the file, then register it inside `if(BUILD_TESTING)`:
  ```cmake
  ament_add_pytest_test(test_x test/test_x.py TIMEOUT 30)                       # plain pytest
  find_package(launch_testing_ament_cmake REQUIRED)
  add_launch_test(test/test_x.py TIMEOUT 120
    ENV ROS_DOMAIN_ID=<unused number> ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)  # starts nodes
  ```
  Add every package the test imports or starts as a `<test_depend>` in `package.xml`. CI installs only build and test dependencies.
- **Telemetry:** add `telemetry/tests/test_<x>.py`; `conftest.py` makes `inav_telemetry` importable and gives you `reply(hex)`.
- **Slow, or needs Gazebo:** don't register it with colcon. Add a step to `test_sim_flight.py`.
- **A known bug you can't fix now:** write the test anyway, mark it `@pytest.mark.xfail(strict=True, reason="…")`. Strict means pytest flags the day it starts passing, so the mark gets removed. In a launch test use `@unittest.skip("…")`, because launch_testing reports `expectedFailure` as a failure.
- **New recordings:** record with `msp_inventory.py capture`, put them in `telemetry/inav/captures/inav/msp/captures/`, **copy them** to `drone_fc_bridge/test/data/` (or `test_capture_copies.py` fails), update the expected values in `test_captures.py`, `test_decoders.py` and `test_inav_decode.cpp`.
- Before pushing: `./scripts/run_tests.sh` and the telemetry tests. **Prove the test can fail**: break the code it guards once and watch it go red. The team did this for every safety test (dates in [CHANGES.md](../seame-docker/CHANGES.md), "Checked" lines).

---

## 12. Bugs the tests have found

| # | Bug | Where | Found by | Effect | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | After a bad CRC the parser threw away the whole length the broken header claimed, including good replies inside it | `inav_telemetry.py` `_next_frame` | `test_msp_frame.py` (real damaged frame from `radio_off`) | lost replies on a noisy link; `MSP_BOXNAMES` needed retries | **Fixed** Nov 12 (drops only `$X` and rescans). Still open in Python: no `skip_pending()` at the timeout, unlike C++ |
| 2 | Disarm while the radio has control was forgotten; when control came back the mission held, and **climbed by itself once re-armed** | `drone_mission/logic.py` | `test_stack.py`, then `test_logic.py` | unsafe climb after re-arming | **Fixed** Nov 12 |
| 3 | Mission commands stalled 0.3–0.8 s (rclpy's multi-threaded executor missed the 20 Hz timer), so fc_bridge timed out and goals aborted with "rangefinder lost" | `drone_mission/mission.py` | `test_stack.py`, `test_sim_flight.py` | jerky flight; flaky CI; nightly failed at the square | **Fixed** Nov 12: single-threaded executor, `execute()` awaits the next tick |
| 4 | `flow_model` prints a `KeyboardInterrupt` traceback on every shutdown | `drone_sim_sensors/flow_model.py` | nightly logs | cosmetic | **Open**: catch `KeyboardInterrupt` in `main()` (the new `estimator_node.py` has the same pattern) |
| 5 | Simulator-mode and unused bits listed as arming blockers | `inav_telemetry.py` `arming_fields` | writing the C++ decoders | INAV SITL would always say "can't arm: simulator" | **Fixed** Nov 12 |
| 6 | Rangefinder 0 cm reported as a valid 0.0 m (INAV sends 0 when none is running) | `inav_telemetry.py` `d_rangefinder` | same | telemetry shows the drone "at 0.00 m" with no sensor | **Fixed** Nov 12 |
| 7 | Power, mAh and mWh drawn read unsigned | `inav_telemetry.py` `d_inav_analog` | same | a negative current showed ~42 949 kW | **Fixed** Nov 12 |
| 8 | `test_stack.py`'s own node on a multi-threaded executor starved its radio stick player for > 0.3 s | `test_stack.py` | its failing logs | the radio seemed to let go mid-test | **Fixed** Nov 12 |
| 9 | The estimator became `fc/odom`'s publisher, but `test_stack.py` started neither it nor `flow_model`, and `fake_drone.py` didn't publish `/sim/ground_truth`; `test_launch_files.py` didn't expect the new node | `drone_bringup` tests | `run_tests.sh`, Nov 13 (`32cfee3`) | 4 failures; the mission had no odometry | **Fixed** Nov 13 (`7325660`, `f9d11ea`, `38c4384`, `f4e9ef2`) |

---

## 13. What isn't tested yet, in priority order

Ordered by how much risk each closes for **flying the real drone**, which is the project's next milestone. Plan IDs from [CI_Tests.md](./CI_Tests.md).

| # | Gap | Why it matters | Proposed test | Effort |
| --- | --- | --- | --- | --- |
| 1 | **fc_bridge `inav` backend using `fc_msp`** (ROS-6 step B) | the code that will talk to the real drone has no end-to-end test | a **fake flight controller**: a small TCP server answering MSP with the recorded replies; start fc_bridge `backend:=inav` against it and check `fc/attitude`, `fc/range`, `fc/status`, `fc/battery`, and what happens on loss, late and damaged replies | Medium |
| 2 | **Required status checks** on `main` (E9) | today a red PR can still be merged by hand | GitHub settings → Branches | Settings only |
| 3 | **Lint for `drone_fc_bridge`** (E2) | the most safety-critical C++ has no style or static checks | `ament_lint_auto` + one reformat commit | Small |
| 4 | **fc_bridge with the real `sim.yaml`** (B2) | the flying configuration (MTF-02P limits, `publish_odom: false`) is only covered indirectly | launch test with `parameters=[sim.yaml]`, noise 0 | Small |
| 5 | **Rerun and refresh the nightly numbers** with the estimator | the square was measured with fc_bridge's odometry, not the estimator's | `./scripts/sim_flight_test.sh`, update section 8.2 | Small |
| 6 | **Flow vs ground truth in flight** | the estimator's real error in Gazebo isn't checked by CI | nightly step using `flow_check.py`'s maths: flow-derived speed within X cm/s of Gazebo's | Small |
| 7 | Telemetry poll loop (A4) and the **port default** | the tool people use daily can break while decoders pass | fake client with canned replies; fix the 5760/23 default | Small |
| 8 | **Link latency in the sim** (Sprint 2: "add sensor values and delay") | the sim assumes an instant link; the real one has a 40–100 ms median and ~0.8 s p95 | a delay/drop node between fc_bridge and Gazebo, and a nightly step that flies with the measured distribution | Medium |
| 9 | INAV SITL nightly (A5) | protocol changes at the next INAV upgrade | build INAV 9.1.x SITL, point `inav_telemetry.py` at it | Medium |
| 10 | `watchdog`, `setpoint_pub`, `demo_flight`, `safety_manager` node, `radio_teleop` node with real axis signs (C1, C3, C5) | small nodes with no test of their ROS wiring | one launch test each | Small each |
| 11 | Flight test in every world (D2), radio in the sim (D3) | worlds are checked as files, only the default one is flown | loop over worlds in `nightly.yml`; fake `/joy` | Medium |
| 12 | `shellcheck` on scripts, flake8 on `tools/` and `scripts/*.py`, coverage (E4–E6) | scripts never checked | add steps to `ci.yml` | Small |
| 13 | Remove `Develop` from triggers, decide on `staging` (E10) | `staging` pushes run no CI | edit `ci.yml` | Tiny |

## 14. Questions to settle

Ask these of the people named in brackets (by area, from the team table in the [README](../README.md#team)).

1. **Which ESP firmware is current: esp-link (TCP 23) or the MicroPython bridge (TCP 5760)?** The telemetry docs and the Nov 12 measurements say esp-link. The tool defaults and the root README said MicroPython. The default port in `inav_telemetry.py` and `latency_test.py` depends on the answer. *(INAV/telemetry owners)*
2. **Is the deletion of the root `TESTS.md` final?** Several docs still link to it (`docs/TESTS.md`, `seame-docker/README.md`, `docs/CI_Tests.md`). If this page replaces it, those links should point here.
3. **Who watches the nightly?** It doesn't block anything, and GitHub only emails the last editor of the cron line. Has it run on `main` yet?
4. **Should `main` require the CI checks** (E9)? Who has admin rights on the repo?
5. **Optical flow sign on the real drone:** the C++ decoder notes that no captured flow rate is ever negative, which suggests INAV 9.1.0 sends negative rates as 0. If that's true, the real drone can't sense motion in half the directions over MSP. It needs a recording while sliding the drone **both** ways. *(INAV owners)* This decides whether the `inav` backend can use MSP optical flow at all, or must rely on INAV's own position estimate (`MSP2_INAV_FULL_LOCAL_POSE`).
6. **Should CI also run the telemetry tests on the dev image**, so laptop and CI use the same Python? Today it uses GitHub's Python 3.12, which matches by luck.
7. **When new recordings are made** (radio bound, MTF-02P fitted, moving), who updates the expected values in three suites (Python decoders, Python captures, C++ decoders)?
8. **Should the nightly gate sim PRs?** It runs on them but can't block them.

---

## 15. Words used on this page

| Word | Meaning |
| --- | --- |
| **CI** | Continuous integration: GitHub runs the tests on every push and PR |
| **Job / step** | A workflow has jobs (run in parallel on separate machines); a job has steps (run in order) |
| **Artifact** | Files a workflow run keeps for download (logs, XML reports, rosbags) |
| **MSP** | MultiWii Serial Protocol: how a computer talks to INAV. We use version 2 |
| **CRC** | A check number computed from a frame's bytes; if a byte changes on the way, it no longer matches. MSP v2 uses CRC-8/DVB-S2 |
| **Decoder** | Turns a reply's raw bytes into numbers with units |
| **Recording / capture** | Real replies from the drone saved to a `.jsonl` file and replayed in tests |
| **Launch test** | A test that starts real ROS nodes (`launch_testing`) and talks to them from a test node |
| **GoogleTest (gtest)** | The C++ unit-test framework |
| **Ground truth** | Where Gazebo says the drone really is; the drone only has its own estimate |
| **Headless** | Gazebo with no window (`gz sim -s`), as on CI machines |
| **xfail (strict)** | A test that documents a known bug without turning CI red; strict flags the day the bug is fixed |
| **SITL** | Software in the loop: INAV's firmware compiled to run on a PC |
| **Flaky** | Passes or fails at random on the same code. Always a real problem, usually timing |

# Tags

#tests
