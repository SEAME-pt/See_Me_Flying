## Contents

1. [At a glance](#1-at-a-glance)
2. [How CI finds and runs the tests](#2-how-ci-finds-and-runs-the-tests)
3. [Telemetry tests (the MSP link to INAV)](#3-telemetry-tests-the-msp-link-to-inav)
4. [The sim's setup, checked without running it](#4-the-sims-setup-checked-without-running-it)
5. [ROS nodes, one at a time](#5-ros-nodes-one-at-a-time)
6. [The whole ROS stack without Gazebo: `test_stack.py`](#6-the-whole-ros-stack-without-gazebo-test_stackpy)
7. [Flight in Gazebo, nightly: `test_sim_flight.py`](#7-flight-in-gazebo-nightly-test_sim_flightpy)
8. [Lint and style checks](#8-lint-and-style-checks)
9. [Docker image build](#9-docker-image-build)
10. [Bugs the tests have found](#10-bugs-the-tests-have-found)
11. [How to run the tests](#11-how-to-run-the-tests)
12. [How to add a test](#12-how-to-add-a-test)
13. [What isn't tested yet](#13-what-isnt-tested-yet)
14. [Words used in this file](#14-words-used-in-this-file)

---

## 1. At a glance

**Cases** counts each check pytest or unittest reports, so a parametrized test counts once per row. **Time** is from the last full run (`scripts/run_tests.sh`, 2026-11-10). Totals are from 2026-11-12: CI's own commands on commit `581471b`, in a fresh `ros:jazzy` container.

| Area | File | Cases | Time | Run by | Added by |
| --- | --- | --- | --- | --- | --- |
| MSP framing | [telemetry/tests/test_msp_frame.py](telemetry/tests/test_msp_frame.py) | 32 | < 1 s | CI `telemetry-python` | jit-23 |
| MSP decoders | [telemetry/tests/test_decoders.py](telemetry/tests/test_decoders.py) | 59 | < 1 s | CI `telemetry-python` | jit-23 |
| Real drone recordings | [telemetry/tests/test_captures.py](telemetry/tests/test_captures.py) | 47 | < 1 s | CI `telemetry-python` | jit-23 |
| Copies of the recordings | [telemetry/tests/test_capture_copies.py](telemetry/tests/test_capture_copies.py) | 2 | < 1 s | CI `telemetry-python` | jit-23 |
| Drone limits in `sim.yaml` | [drone_bringup/test/test_config.py](seame-docker/ros2_ws/src/drone_bringup/test/test_config.py) | 17 | < 1 s | CI `ros2-build-test` | jit-23 |
| What the launch file starts | [drone_bringup/test/test_launch_files.py](seame-docker/ros2_ws/src/drone_bringup/test/test_launch_files.py) | 24 (1 skipped in CI) | about 1 s | CI `ros2-build-test` | jit-23 |
| Gazebo worlds | [drone_bringup/test/test_worlds.py](seame-docker/ros2_ws/src/drone_bringup/test/test_worlds.py) | 9 (8 skipped in CI, 2 in the dev container, until `feature/153` is merged) | < 1 s | CI `ros2-build-test` | jit-23 |
| Mission state machine | [drone_mission/test/test_logic.py](seame-docker/ros2_ws/src/drone_mission/test/test_logic.py) | 44 | < 1 s | CI `ros2-build-test` | João Barros |
| Command arbitration | [drone_safety/test/test_arbiter.py](seame-docker/ros2_ws/src/drone_safety/test/test_arbiter.py) | 9 | < 1 s | CI `ros2-build-test` | João Barros |
| Radio switches and sticks | [drone_basics_py/test/test_radio_teleop.py](seame-docker/ros2_ws/src/drone_basics_py/test/test_radio_teleop.py) | 24 | < 1 s | CI `ros2-build-test` | João Barros |
| Optical flow model | [drone_sim_sensors/test/test_flow_model.py](seame-docker/ros2_ws/src/drone_sim_sensors/test/test_flow_model.py) | 11 | < 1 s | CI `ros2-build-test` | David Roque |
| fc_bridge failsafes | [drone_fc_bridge/test/test_failsafes.py](seame-docker/ros2_ws/src/drone_fc_bridge/test/test_failsafes.py) | 9 | 19 s | CI `ros2-build-test` | João Barros |
| fc_bridge state outputs | [drone_fc_bridge/test/test_state.py](seame-docker/ros2_ws/src/drone_fc_bridge/test/test_state.py) | 7 | 6 s | CI `ros2-build-test` | João Barros |
| fc_bridge services | [drone_fc_bridge/test/test_services.py](seame-docker/ros2_ws/src/drone_fc_bridge/test/test_services.py) | 4 | 6 s | CI `ros2-build-test` | João Barros |
| fc_bridge `inav` backend | [drone_fc_bridge/test/test_inav.py](seame-docker/ros2_ws/src/drone_fc_bridge/test/test_inav.py) | 3 | < 1 s | CI `ros2-build-test` | João Barros |
| MSP framing for the real drone (C++) | [drone_fc_bridge/test/test_msp.cpp](seame-docker/ros2_ws/src/drone_fc_bridge/test/test_msp.cpp) | 21 | < 1 s | CI `ros2-build-test` | João Barros |
| INAV decoders for the real drone (C++) | [drone_fc_bridge/test/test_inav_decode.cpp](seame-docker/ros2_ws/src/drone_fc_bridge/test/test_inav_decode.cpp) | 16 | < 1 s | CI `ros2-build-test` | João Barros |
| Whole stack, no Gazebo | [drone_bringup/test/test_stack.py](seame-docker/ros2_ws/src/drone_bringup/test/test_stack.py) + [fake_drone.py](seame-docker/ros2_ws/src/drone_bringup/test/fake_drone.py) | 5 | 60 s | CI `ros2-build-test` | jit-23 |
| Flight in Gazebo | [drone_bringup/test/test_sim_flight.py](seame-docker/ros2_ws/src/drone_bringup/test/test_sim_flight.py) | 8 steps | 90 s + Gazebo | [nightly.yml](.github/workflows/nightly.yml) | jit-23 |
| Lint and style | `test_flake8.py`, `test_pep257.py`, … in each package | 33 | about 10 s | CI `ros2-build-test` | package templates |
| Telemetry syntax and lint | `telemetry/*.py` | (job steps) | seconds | CI `telemetry-python` | — |
| Docker image | [seame-docker/Dockerfile](seame-docker/Dockerfile) | (job step) | minutes | CI `docker-image` | — |

**Totals:**
- `colcon test` (all ROS packages): 236 cases, 203 behaviour and 33 lint, in 80–105 s. 14 are skipped in CI, which has no Gazebo, `ros_gz` or `joy`, and 7 in the dev container (section 2 lists them). colcon's own summary says 254: it also counts the 18 CTest entries, which wrap cases already counted.
- `pytest telemetry`: 140 cases, all passed, under 1 s.
- Nightly: 8 flight steps.

**Where each one is in git:**
- On `main`: the ROS node tests (mission, safety, radio, flow), the fc_bridge launch tests and its two C++ tests, the drone recordings and their copies in `drone_fc_bridge/test/data/`, the lint checks, `scripts/run_tests.sh` and `scripts/test_report.py`.
- On `ci/test_implementation` only (committed and pushed, not on `main` yet): the telemetry tests, the pytest step in `ci.yml`, `test_config.py`, `test_launch_files.py`, `test_worlds.py`, `test_stack.py` and `fake_drone.py`, `test_sim_flight.py` with `nightly.yml` and `scripts/sim_flight_test.sh`, the `headless` launch option, and the bug tests added to `test_logic.py`, `test_msp_frame.py` and `test_decoders.py` (expected fails until those bugs were fixed on Nov 12).

---

## 2. How CI finds and runs the tests

### The workflows

GitHub runs every file in [.github/workflows/](.github/workflows/) as its own workflow, started by that file's own `on:` section. The two files don't call each other.

**[ci.yml](.github/workflows/ci.yml) runs on every push and pull request** to `main`, `Develop`, `test` and `ci/**`, and from the "Run workflow" button.

| Job | What it does |
| --- | --- |
| `ros2-build-test` | In a clean `ros:jazzy` container: installs only build and test dependencies with `rosdep` (no Gazebo, so it's fast), then runs `colcon build`, `colcon test` and `colcon test-result --verbose`. Uploads the result files as the `ros2-test-results` artifact. |
| `telemetry-python` | Python 3.12: `py_compile` on `telemetry/*.py` (syntax), `flake8 telemetry --max-line-length=140` (lint), then `pytest telemetry -v` (the telemetry tests). |
| `docker-image` | Builds `seame-docker/Dockerfile` from scratch, without pushing it, using GitHub's layer cache. |
| `block-red-pr` | If any job above failed on a PR, moves the PR back to draft and comments with a link to the run. |

**[nightly.yml](.github/workflows/nightly.yml) runs every night at 02:00 UTC**, from the "Run workflow" button, and on PRs that change the sim (launch files, config, the flight test or its script).

| Job | What it does |
| --- | --- |
| `gazebo-flight` | Builds the dev image (`seame/ros2-dev:jazzy`) from the `docker-image` job's cache, runs [scripts/sim_flight_test.sh](seame-docker/scripts/sim_flight_test.sh), and uploads the `sim-flight` artifact for 14 days. The artifact holds the test log, the xUnit report, a rosbag of the flight and every node's log. Not part of `block-red-pr`. |

`schedule:` and the "Run workflow" button only work once `nightly.yml` is on `main`. Until then it runs only on PRs that touch the sim.

### How each kind of test is found

| Where the test is | How it is found | So, to add one |
| --- | --- | --- |
| A **Python ROS package** (`drone_mission`, `drone_safety`, `drone_basics_py`, `drone_sim_sensors`) | `colcon test` runs pytest on the package's `test/` folder, which picks up every `test_*.py`. | Drop a `test_*.py` file in `test/`. |
| A **C++/CMake ROS package** (`drone_bringup`, `drone_fc_bridge`, `drone_basics_cpp`) | Only tests **registered in `CMakeLists.txt`** run: `add_launch_test(...)` for launch tests, `ament_add_pytest_test(...)` for plain pytest. `ament_lint_auto_find_test_dependencies()` adds the linters listed in `package.xml`. | Register the file in `CMakeLists.txt` and add its `<test_depend>`s to `package.xml`. |
| **`telemetry/`** (plain Python, not a ROS package) | colcon never sees it. The `telemetry-python` job runs `pytest telemetry`. [telemetry/tests/conftest.py](telemetry/tests/conftest.py) makes `inav_telemetry` importable. | Drop a `test_*.py` file in `telemetry/tests/`. |
| **`test_sim_flight.py`** | Deliberately **not** registered, so `colcon test` never runs it (too slow for every PR). It still gets linted. The nightly runs it through `scripts/sim_flight_test.sh`. | Add a step to it, or a new unregistered file run by the script. |

### Keeping tests apart from other running sims

Launch tests start real ROS nodes, so they could hear a sim running on the same machine, or another laptop on the lab Wi-Fi. Each one gets its own ROS domain and stays on localhost:

| Tests | Environment |
| --- | --- |
| fc_bridge launch tests | `ROS_DOMAIN_ID=199`, `ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST` (set in `CMakeLists.txt`) |
| `test_stack.py` | `ROS_DOMAIN_ID=198`, localhost only (set in `CMakeLists.txt`) |
| `test_sim_flight.py` | `ROS_DOMAIN_ID=196`, localhost only, `GZ_PARTITION=flight_test`, a separate Gazebo channel (set by `sim_flight_test.sh`) |

### How CI was doing on Nov 12

From GitHub's Actions page (commit `581471b`, this branch with `main` merged in), and from CI's exact commands rerun on the same commit in a clean `ros:jazzy` container, which shows each test case. GitHub only shows the per-test logs to logged-in members.

| Workflow and job | What it runs | Last result on GitHub | Notes |
| --- | --- | --- | --- |
| `ci.yml` `telemetry-python` | syntax, flake8, `pytest telemetry` (140 cases) | passed (13 s) | the 4 expected fails are reported as xfail, not as failures. **Fixed since** (Nov 12): all 140 pass, none marked xfail |
| `ci.yml` `ros2-build-test` | `colcon build`, `colcon test` (236 cases) | passed (170 s; tests 103 s) | `test_stack.py` is **flaky**: on this commit it failed 3 times in 6 runs on Nov 12 (once with CI's exact commands, twice in 5 repeats), so GitHub's green was partly luck. The cause is bug 3: the mission runs up to half a second behind. It handled a "disarmed" status after the test had already re-armed, and dropped the `Takeoff` as "disarmed"; another time `Takeoff` wasn't accepted within 5 s. Everything else passed in every run. **Fixed since** (Nov 12): with bug 3 fixed and the test's own node on one thread (bug 8), it passed 6 runs out of 6 ([section 6](#6-the-whole-ros-stack-without-gazebo-test_stackpy)). |
| `ci.yml` `docker-image` | builds the dev image | passed (18 s, from the cache) | |
| `ci.yml` `block-red-pr` | only on PRs | skipped (a push, not a PR) | if `test_stack.py` fails by chance on a PR, this moves the PR back to draft |
| `nightly.yml` `gazebo-flight` | the Gazebo flight | **never ran on GitHub** | it starts only on a PR that touches the sim, or every night once `nightly.yml` is on `main`. Run by hand on this commit (Nov 12, `scripts/sim_flight_test.sh`): **every step passed** in 121 s (sides 0.91–0.98 m, the square closes within 0.076 m, landed, the killed mission stopped in 0.97 s). An earlier run with the same mission code failed at the square ("rangefinder lost"), so bug 3 made it flaky too. **With bug 3 fixed** (Nov 12): every step passed again (sides 0.89–0.91 m, the square closes within 0.099 m, the killed mission stopped in 1.05 s). |

**Known bugs kept from turning CI red on that commit, on purpose.** Each was still a test that ran; it just expected the bug, and `strict=True` makes it fail the day the bug is fixed, so the mark gets removed. All of them are fixed now:
- 4 expected fails in the telemetry tests: bugs 1, 5, 6 and 7 in `inav_telemetry.py`. **Fixed since** (Nov 12): those 4 tests now pass ([section 10](#10-bugs-the-tests-have-found));
- 1 expected fail in `test_logic.py` and 1 skip in `test_stack.py`: bug 2 (a disarm under the radio is forgotten). **Fixed since** (Nov 12): both tests now run and pass.

No lint rule was turned off, no CI step is allowed to fail, and no test retries a failure. The two `Takeoff` helpers only resend a Takeoff the mission *refused* on the ground while its rangefinder settles (at most 5 s, 30 s in Gazebo), as the mission's own demo does. Once accepted, any abort fails the test. One old test was removed: `test_unknown_arming_bit_is_kept`, which expected the wrong arming behaviour (bug 5).

**Skipped in CI (16 on that commit, 14 since bug 2 was fixed), all on purpose:**

| Skipped | Why |
| --- | --- |
| `test_copyright` in 4 Python packages, cppcheck on `watchdog.cpp` | no license headers yet; cppcheck 2.13 is too slow |
| `test_disarm_while_the_radio_flies` (`test_stack.py`), `test_disarm_while_overridden_is_not_forgotten` (`test_logic.py`) | bug 2. **Fixed since** (Nov 12): both run and pass now |
| 6 world checks for `multicopter_velocity_control.sdf`, `test_other_programs_are_installed` | Gazebo, `ros_gz` and `joy` are not installed in CI; the dev container runs them |
| `test_every_model_has_its_files`, `test_worlds_and_models_are_installed` | no worlds or models in `drone_bringup` until `feature/153` is merged |

**Other branches:** `main`'s last run passed (Nov 12). The commit before this one, `1af31c9`, failed: lint errors in `test_config.py` (blank lines, a trailing space, the docstring's first line), fixed since. `feature/153` (the new world) has **never run CI**: its branch name isn't in the triggers and it has no PR yet, so its lint error (a 119-character line in `sim.launch.py`) will show up only when its PR is opened.

---

## 3. Telemetry tests (the MSP link to INAV)

**What's being tested:** [telemetry/inav_telemetry.py](telemetry/inav_telemetry.py) talks to the flight controller (INAV 9.1.0) through the ESP's TCP bridge, using the MSP v2 protocol. Every message is a frame:

```
'$' 'X' dir | flag | command (2 bytes) | size (2 bytes) | payload | checksum
dir: '<' request, '>' reply, '!' error reply      checksum: CRC-8/DVB-S2
```

The code has two layers, and the tests check both:
- the **frame layer**, which builds requests, finds replies in the byte stream and checks their checksum;
- the **decoders**, which turn a payload's raw bytes into numbers with the right units, like degrees, metres and volts.

None of these tests need the drone or a network.

### 3.1 `conftest.py`: shared setup

[telemetry/tests/conftest.py](telemetry/tests/conftest.py) puts `telemetry/` on Python's path, so the tests can `import inav_telemetry`. It also provides `reply(hex)`, which splits a recorded reply into its command and payload after checking that the frame is whole.

### 3.2 `test_msp_frame.py`: framing (32 cases)

**How:** feeds bytes straight into the reply parser (`MSPClient._next_frame`), and tests `MSPClient.request()` against a **fake socket** that returns chosen chunks of bytes and then times out like the real one. The real frames it uses were recorded from the drone.

**What it checks:**
- **Checksum:**
  - Gives the published CRC-8/DVB-S2 value for `"123456789"` (0xBC). That number comes from the CRC standard, not from our code.
  - Matches the checksum on real frames from the drone.
  - Notices every single flipped bit in a frame.
- **Request frames:** the layout (`$X<`, flag, command, size, checksum); a request with a payload; 2-byte little-endian command numbers (needed for MSP v2 commands like `0x2001`); the same header layout as the drone's replies.
- **Reply parser:**
  - reads a real reply, and several replies back to back in the right order;
  - skips garbage before a frame;
  - drops a frame with a bad checksum and still reads the next one;
  - reports an error reply (`$X!`) as "not ok";
  - ignores our own request if it's echoed back;
  - skips a header with an impossible size;
  - waits when a frame is cut in half, or when the `$` and `X` arrive in different reads.
- **`request()`:** sends the right bytes and returns the payload; puts a reply together from several reads; skips a late reply to an earlier command; returns "not ok" on an error reply; gives up after the timeout (0.2–0.5 s); raises an error when the connection closes.
- **A good reply hidden inside a damaged one is recovered:** `test_valid_reply_inside_a_corrupt_one_is_recovered`, an expected fail until [bug 1](#10-bugs-the-tests-have-found) was fixed.

**Errors it catches:** a broken checksum, which would make every real reply look damaged, or let damaged ones through; wrong byte order in command numbers, so the drone answers the wrong message; a parser that loses its place after noise, after a damaged frame or across TCP reads; replies matched to the wrong request; the program hanging forever when the drone goes quiet.

**Why it helps:** the link to the drone is noisy Wi-Fi and serial. These are exactly the situations that happen in flight and are hard to reproduce by hand. Each one is checked here in milliseconds, on every push.

### 3.3 `test_decoders.py`: decoders (59 cases)

**How:** two kinds of input:
- payloads built by hand with `struct.pack`, with chosen values, to pin down the units;
- real payloads from the drone, checked against what the drone was doing when they were recorded.

**What it checks:**
- **Units and scaling:** attitude in tenths of a degree; altitude in cm → m; IMU axis order; signed optical-flow rates; battery voltage and current scaling and flags; every battery state; GPS degrees, with HDOP optional; rangefinder cm → m, and −1 means out of range.
- **Lists and text:** a list of 16-bit numbers ignores a stray odd byte at the end; text loses its padding; mode names are split correctly.
- **Bit fields:**
  - each sensor bit maps to the right name;
  - "armed" is not listed as a reason the drone can't arm;
  - arming blockers come out named, in bit order;
  - flight modes come from the drone's own mode names, and a mode without a name is still reported.
- **Status messages:** every field of `MSP2_INAV_STATUS`, including the older reply without the mixer profile; `MSP_STATUS` and `MSP_STATUS_EX`.
- **Real data from the drone:** identity (INAV 9.1.0, API 2.5) and the drone's mode names.
  - Attitude in three states: flat, tilted about 46°, radio off.
  - The IMU's gravity agrees with the tilt; status flat vs "not level"; battery 16.16 V.
  - Optical flow while moving: quality 92, flow 46 °/s.
  - RC channels and motors.
- **Robustness:** a short or odd-sized payload, given to every decoder, may only raise the two errors `poll()` catches (`struct.error`, `IndexError`). Anything else would crash the telemetry program.
- **Command numbers:** each entry asks INAV 9.1.0 for the right MSP command.
- **Output:** a raw payload is hex in JSON and decimal bytes on screen.

**Errors it catches:** a value off by ×10 or ×100 (tenths vs whole degrees, cm vs m, centivolts); swapped axes; signed read as unsigned (negative flow read as a huge positive); a bit field shifted by one, which names the wrong flight mode or blocker; a crash when the drone sends a shorter reply; asking for the wrong message number.

**Why it helps:** wrong units don't crash anything. They just show wrong numbers, and someone trusts them in flight. These tests pin every unit to a known value.

**Fixed bugs (3 tests, at the end of the file):** fc_bridge's C++ decoders on `main` (`drone_fc_bridge/src/inav_decode.cpp`, ROS-6 step A) were written from the INAV 9.1.0 source, and their comments named three places where `inav_telemetry.py` was wrong. All three were fixed on Nov 12. Each one is a test that says what INAV really sends, so the bug can't come back:

| Test | What INAV does | What the script did before the fix |
| --- | --- | --- |
| `test_only_real_arming_blockers_are_listed` | Only bits 6–16 and 18–30 are reasons not to arm. Bits 4 and 5 mean "running as a simulator" (set on INAV SITL). | Listed every set bit, so a SITL drone showed `simulator_sitl` as a reason it can't arm. |
| `test_rangefinder_zero_is_not_a_distance` | Sends 0 cm when no rangefinder is running (it turns a real 0 into −1). | Reported a valid 0.0 m. That's the reply in every recording, because no rangefinder is fitted. |
| `test_inav_analog_negative_power_and_drawn` | Power, mAh drawn and mWh drawn are signed numbers. | Read them unsigned, so a negative current showed a power of about 42 949 kW. |

They replace an older test, `test_unknown_arming_bit_is_kept`, which expected the wrong arming behaviour. See [section 10](#10-bugs-the-tests-have-found).

### 3.4 `test_captures.py`: replaying real drone recordings (47 cases)

**The data:** [telemetry/inav/captures/inav/msp/captures/](telemetry/inav/captures/inav/msp/captures/) holds four `.jsonl` files from issue #125, explained in [the captures README](telemetry/inav/captures/README.md). They contain every raw MSP reply the drone sent, about 20 per message, recorded on the bench: OddityRC F7, INAV 9.1.0, esp-link bridge, props off.

| Recording | What the drone was doing |
| --- | --- |
| `flat_still` | lying still, almost level |
| `tilted` | rolled about 46° |
| `radio_off` | radio off, so INAV is in failsafe |
| `flow_moving` | slid by hand over a surface, so the optical flow sees motion |

The files are only data: the telemetry program never uses them.

**How:** sends every recorded reply through the real parser and decoders, then compares the results with what the drone was doing.

**What it checks:**
- **The recordings themselves:** the header is right, there are enough good replies, and timeouts have no data.
- **Framing, for every frame:**
  - every good reply is whole and has a valid checksum;
  - the parser reads every good reply;
  - the parser rejects every damaged reply;
  - every good reply decodes completely, never falling back to raw bytes.
- **Per state:**
  - `flat_still`: roll between −2° and 0°, pitch between −7° and −5°, heading 48°/49°, gravity straight down Z.
  - `tilted`: roll between 44° and 48°, gravity split evenly between Y and Z, INAV reports "not level".
  - `radio_off`: FAILSAFE is the only mode, "no RC link" is listed as a reason it can't arm, it's not armed, and throttle is at its failsafe value of 885.
  - `flow_moving`: flow reaches at least 40 °/s (the fastest is about 56 °/s), quality drops to 0 at least once, and is 100 most of the time.
  - The three still states have flow under 25 °/s.
- **Same in all four:** identity INAV 9.1.0 and API 2.5; ARM at index 0 and FAILSAFE at 17 of the mode names; disarmed; sensors exactly acc, baro, opflow and temp (no rangefinder fitted yet); motors stopped (1000); battery 16.0–16.4 V, 4 cells, "ok".

**Errors it catches:** everything sections 3.2 and 3.3 catch, but with hundreds of real frames rather than a few. A decoder change that breaks only some real messages. An INAV setting changed on the drone that changes its replies, if you record new captures.

**Limits:** these are bench recordings. They don't cover flight, the radio switched on, or the rangefinder, because it isn't fitted yet. Those need new recordings, made with `telemetry/inav/captures/msp_inventory.py`.

### 3.5 `test_capture_copies.py`: the C++ tests use the same recordings (2 cases)

**Why it exists:** on `main`, fc_bridge's C++ tests read **copies** of the four recordings, in `seame-docker/ros2_ws/src/drone_fc_bridge/test/data/`, because only `ros2_ws` is mounted in the dev container. Their README says "if the captures are redone, copy them here again". If someone forgets, the C++ tests and the Python tests quietly check different data.

**What it checks:**
- the four recordings are where the tests expect them (otherwise the next check would skip without anyone noticing);
- every file under `seame-docker/ros2_ws/src` with the name of a recording is byte-for-byte the same as the original. If one differs, the failure prints the `cp` command that fixes it.

With `main` merged in, both checks run, and they pass: the four copies are identical. Adding one line to a copy makes it fail. If you copy `telemetry/` somewhere outside the repo to run the tests (as in [section 11](#telemetry-tests)), the second check skips, because there's no `ros2_ws` next to it.

**Where it runs:** CI's `telemetry-python` job, because that job checks out the whole repo.

---

## 4. The sim's setup, checked without running it

Three plain-pytest files in `drone_bringup`. They read the sim's configuration, launch file and worlds without starting anything, so together they take about 2 s and run on every PR.

### 4.1 Drone limits: `test_config.py`

**Where:** [seame-docker/ros2_ws/src/drone_bringup/test/test_config.py](seame-docker/ros2_ws/src/drone_bringup/test/test_config.py). It's registered in drone_bringup's `CMakeLists.txt` with `ament_add_pytest_test`.

**What it reads:** [config/sim.yaml](seame-docker/ros2_ws/src/drone_bringup/config/sim.yaml), which has one section per ROS node (fc_bridge, mission, safety_manager, radio_teleop, …), and [launch/sim.launch.py](seame-docker/ros2_ws/src/drone_bringup/launch/sim.launch.py). It starts no nodes.

**What it checks (17 cases):**

| Rule | Why |
| --- | --- |
| `mission.max_vz` == `fc_bridge.max_speed_z` | If the mission plans faster climbs than fc_bridge allows, fc_bridge cuts them silently and the mission's timing is off. |
| `safety_manager.source_timeout_s` == `fc_bridge.setpoint_timeout_s` | The two timeouts must agree on when a silent source counts as lost. |
| Mission `speed`, `land_speed`, `yaw_rate`; setpoint_pub `speed`, `climb_speed`; radio_teleop `max_xy`, `max_z`, `max_yaw`: each is > 0 and ≤ the matching fc_bridge limit (8 rows) | Any command above the limit would be clamped without warning. |
| `range_min` < `ground_h` < `target_h` < `range_max` | The takeoff height must be readable by the rangefinder, and "on the ground" must be above its minimum. |
| `ground_h` < `demo_flight.height` < `range_max` | The demo's height must be flyable and measurable. |
| `flow_model.min_height` < `mission.ground_h` | Optical flow must already work when the mission starts counting the drone as flying. |
| `priority[0] == 'radio'` | The pilot must always win. |
| Every `*_s` and `*_hz` value > 0 | A zero or negative time or rate breaks timers. |
| Decimal values are floats (`0.0`, not `0`) | ROS refuses to start a node whose parameter has the wrong type. |
| Every section name is a node started by `sim.launch.py` | A typo in a section name makes that node silently ignore every value in it. |

**Errors it catches:** someone changes a limit in one place but not the other; a typo in `sim.yaml`; a height outside the sensor's range; an int where ROS expects a float. All of these would otherwise only show up as odd behaviour in the sim.

**Why it helps:** it's instant, needs nothing running, and turns "the values must agree" comments in `sim.yaml` into rules that CI enforces.

### 4.2 What the launch file starts: `test_launch_files.py` (24 cases)

**Where:** [seame-docker/ros2_ws/src/drone_bringup/test/test_launch_files.py](seame-docker/ros2_ws/src/drone_bringup/test/test_launch_files.py), registered with `ament_add_pytest_test`.

**How:** `sim.launch.py` decides everything in one function, `setup()`, once the arguments are known. The test calls it the way `ros2 launch` would, but swaps in a `Node`, Gazebo include and timer that only **record** what they were given: which program, which parameters, which remaps, what goes to Gazebo. Nothing starts. It does this for **all 48 combinations** of `backend`, `source`, `radio`, `demo` and `headless`. An argument name the launch file doesn't have is refused, because `ros2 launch` would silently ignore it.

**What it checks:**

| Area | Rule |
| --- | --- |
| Which nodes | The default is the full sim: Gazebo, bridge, `flow_model`, `fc_bridge`, `safety_manager`, `mission`, `joy_node`, `radio_teleop`. `backend:=inav` starts no Gazebo, no bridge, no flow model and no radio nodes. `radio:=false` starts no radio nodes. `demo_flight` only with `demo:=true`. The circle demo starts `setpoint_pub` on a timer, after the rest. `source:=circle` without demo, and `source:=none`, fly nothing. |
| Arming | With the radio (or on the real drone), `fc_bridge` starts disarmed and the mission doesn't arm by itself. Without the radio, `fc_bridge` starts armed and the mission arms. |
| Gazebo | It gets `-r <world>`, and `-s -r <world>` with `headless:=true`. |
| Wiring | `mission` and `setpoint_pub` publish on `/cmd/mission`, `radio_teleop` on `/cmd/radio`, `safety_manager` has no remap. |
| Clock | Every one of our nodes has `use_sim_time` true in the sim and false with `inav`, in all 48 combinations. |
| Config | Every node except the bridge gets `sim.yaml`; every parameter file named exists. |
| Installed | Every program it starts exists in `lib/<package>/`. Gazebo's and joy's are checked only where they're installed (the dev container), so that one test skips in CI. Every package it starts is in drone_bringup's `package.xml`. |
| Safety checks | Every package the launch starts is in the list it checks **before** starting Gazebo (`PACKAGES`, `REAL_PACKAGES`). A missing package stops the launch with an error. `inav` needs none of the sim packages. A second sim in the same partition is refused. |

**Errors it catches:** a program or package renamed; a config file not installed; a node started without `sim.yaml`, so it runs on its code defaults; the real drone starting Gazebo or the radio nodes; a node on the wrong clock; a source publishing straight to `fc_bridge`; an argument renamed; a new package missing from the pre-start check, which used to leave Gazebo running orphaned. Checked by breaking the launch file on purpose four ways (an executable renamed, radio nodes started with `inav`, `use_sim_time` dropped from `flow_model`, `joy` removed from the pre-start check): each was caught.

**Why it helps:** until now, these mistakes were only found by launching the sim by hand, or by the nightly flight hours later.

### 4.3 The Gazebo worlds: `test_worlds.py` (9 cases)

**Where:** [seame-docker/ros2_ws/src/drone_bringup/test/test_worlds.py](seame-docker/ros2_ws/src/drone_bringup/test/test_worlds.py), registered with `ament_add_pytest_test`.

**How:** it reads the `.sdf` world files as XML, and [config/gz_bridge.yaml](seame-docker/ros2_ws/src/drone_bringup/config/gz_bridge.yaml) for the topics our bridge uses. Gazebo is not started.

**Which worlds:** every world in `drone_bringup/worlds/`, plus the launch file's default world (`multicopter_velocity_control.sdf`, which is Gazebo's own). This branch has no `worlds/` folder yet: `outdoor_field.sdf` comes with `feature/153`. Gazebo isn't installed in CI, so there the default world is skipped too. Until `feature/153` is merged, the world checks really run only in the dev container (`run_tests.sh`).

**What it checks, in each world:**
- the physics system is loaded (without it nothing moves);
- exactly one model has a velocity controller on the topics the bridge sends to (`/X3/gazebo/command/twist`, `/X3/enable`): the drone;
- the drone publishes odometry on the topic the bridge reads (`/model/x3/odometry`, which becomes `/X3/odom` and `/sim/ground_truth`);
- the drone starts on the ground (at most 0.5 m up), and its Fuel model is pinned to a version;
- every `model://` it uses exists.

**And once:** the bridge sends to and reads from exactly one drone; every model in `drone_bringup/models/` has its `.sdf` and the textures and meshes it names; worlds and models are installed (`install(DIRECTORY ...)` in `CMakeLists.txt`).

**Errors it catches:** a new world where the drone ignores our commands, has no odometry (fc_bridge never sees it move), or spawns in the air; a missing model or texture; a world that isn't installed. Checked against `feature/153`'s world: all 15 checks pass (both worlds), and four breakages made on purpose (enable topic renamed, drone spawned 3 m up, grass texture deleted, worlds not installed) were each caught by the matching check.

**Why it helps:** a new world is a big file nobody reads line by line. This catches the few lines that matter to us, in a second.

---

## 5. ROS nodes, one at a time

These tests check one node, or the logic inside it. The ones in Python packages call the node's logic directly, without ROS, so they run in milliseconds. The fc_bridge ones are **launch tests**: they start the real fc_bridge program, and a test node plays the parts around it.

### 5.1 Mission state machine: `drone_mission/test/test_logic.py` (44 cases)

**Where:** [seame-docker/ros2_ws/src/drone_mission/test/test_logic.py](seame-docker/ros2_ws/src/drone_mission/test/test_logic.py). It tests [drone_mission/logic.py](seame-docker/ros2_ws/src/drone_mission/drone_mission/logic.py), the brain behind the `Takeoff`, `Goto` and `Land` actions.

**How:** no ROS at all. A toy drone, the "plant", moves exactly as commanded: it stops at the ground, and can optionally sag or hit a ceiling. Its rangefinder reads the height: `-inf` below the minimum range, `+inf` above the maximum. Whole flights run in milliseconds.

**What it checks:**
- **Takeoff:** the full takeoff, hold, land sequence; takeoff to a given height. Refused without a rangefinder reading, above the rangefinder's range, when already in the air, before the reading has been steady for `ready_s`, or when not armed (`radio_arms`). If takeoff times out, the drone lands. Cancelling holds the height reached.
- **Goto:** moves forward, relative to the heading; a square comes back to its start. Refused on the ground, during takeoff, or without odometry. Aborts when odometry stops, gives up after its time limit, sends feedback, and holds position when cancelled.
- **Land:** pre-empts a Goto, can't be cancelled, and is refused on the ground. A Land sent during an automatic landing attaches to it.
- **Height:** hold corrects sag; tilt is corrected; `-inf` means "at the ground".
- **Rangefinder loss:** hovers, then resumes hold; aborts a Goto; lands blind if the loss lasts too long; on the ground it stays grounded; mid-takeoff it holds the height reached.
- **Another source takes over (radio):** the goal is aborted and the mission goes quiet; goals are refused meanwhile. When control comes back it holds where the pilot left it, in the air or on the ground. Repeated messages change nothing.
- **Arming:** with no status yet, "armed" is unknown; without `radio_arms` the node arms itself. A stale "disarmed" status doesn't abort a takeoff. Disarming in the air aborts the goal and goes quiet, and disarming on the ground changes nothing.
- **Disarmed while the radio flies:** the disarm isn't forgotten when control comes back, and re-arming on the ground doesn't climb (`test_disarm_while_overridden_is_not_forgotten`, an expected fail until [bug 2](#10-bugs-the-tests-have-found) was fixed).

**Errors it catches:** wrong state changes; goals accepted when they're unsafe; the drone climbing on its own after something interrupted it; commands still sent after a disarm; a missing landing when the rangefinder is lost.

**Why it helps:** the mission's whole decision logic is tested at the speed of a unit test, including rare situations that are risky to try with a real drone.

### 5.2 Command arbitration: `drone_safety/test/test_arbiter.py` (9 cases)

**Where:** [seame-docker/ros2_ws/src/drone_safety/test/test_arbiter.py](seame-docker/ros2_ws/src/drone_safety/test/test_arbiter.py). It tests [drone_safety/arbiter.py](seame-docker/ros2_ws/src/drone_safety/drone_safety/arbiter.py), which picks which source's commands reach fc_bridge.

**What it checks:**
- nothing is active at start, and a single source is forwarded;
- radio beats mission, and manual beats mission but not radio;
- control returns when the radio goes quiet, and everything quiet means "none";
- an unknown source is never forwarded;
- a change is reported once;
- time going backwards (a sim reset) doesn't count as fresh.

**Errors it catches:** the pilot not getting control; control never coming back; a stale source still driving the drone.

### 5.3 Radio switches and sticks: `drone_basics_py/test/test_radio_teleop.py` (24 cases)

**Where:** [seame-docker/ros2_ws/src/drone_basics_py/test/test_radio_teleop.py](seame-docker/ros2_ws/src/drone_basics_py/test/test_radio_teleop.py). It tests `radio_teleop`, which turns the RadioMaster's joystick messages into arming and stick commands in the sim.

**How:** calls the node's joystick handler directly with made-up `Joy` messages, and records what it would publish. No radio and no launch.

**What it checks:**
- **Arm switch:**
  - must be held for `arm_hold_s` before it counts, so contact bounce doesn't engage it (bounce patterns recorded with `arm_bounce.py`);
  - switching off takes effect immediately;
  - a switch already on at start must be cycled first, as INAV requires;
  - arming is refused with the throttle off centre;
  - switching off disarms even in flight;
  - the flight controller is armed only once.
- **Takeover switch:** does nothing alone, and arming alone doesn't take over. Together with the arm switch it engages after the hold time. Switching it off releases control at once, and so does switching off the arm switch.
- **Sticks:** scaled to the configured limits; zero inside the deadband; re-engaging needs the throttle centred again.
- **Missing axes:** a switch exactly at the threshold, or a missing arm or takeover axis, counts as off.

**Errors it catches:** accidental arming from switch bounce; a drone that won't disarm; a sudden throttle jump when the pilot takes over.

### 5.4 Optical flow model: `drone_sim_sensors/test/test_flow_model.py` (11 cases)

**Where:** [seame-docker/ros2_ws/src/drone_sim_sensors/test/test_flow_model.py](seame-docker/ros2_ws/src/drone_sim_sensors/test/test_flow_model.py). It tests [flow_model.py](seame-docker/ros2_ws/src/drone_sim_sensors/drone_sim_sensors/flow_model.py), the fake optical-flow sensor the sim builds from Gazebo's true motion.

**What it checks:**
- **Signs:** hovering gives no flow; moving forward gives negative flow Y; moving left gives positive flow X; rotating in place gives the body rate.
- **Geometry:** tilt lengthens the distance to the ground; unusable geometry (on the floor, on its side) gives no reading.
- **Rounding:** whole degrees truncate toward zero, as INAV's MSP reply does.
- **Quality and noise:** the measurement passes the ideal flow when there's no noise; quality is 0 when too low or too fast; the noise has the requested spread.

**Errors it catches:** sign mistakes, which make the drone drift the wrong way in the sim; a sim sensor that behaves better than the real MTF-02P.

### 5.5 fc_bridge launch tests: `drone_fc_bridge/test/` (4 files, 23 cases)

**What's being tested:** [fc_bridge.cpp](seame-docker/ros2_ws/src/drone_fc_bridge/src/fc_bridge.cpp) is the only node that talks to the flight controller: Gazebo's X3 in the sim, INAV on the real drone. Each file starts the real `fc_bridge` program alone, on the wall clock, without Gazebo, and a test node plays the other side.

**[test_failsafes.py](seame-docker/ros2_ws/src/drone_fc_bridge/test/test_failsafes.py) (9 cases, about 19 s):**
- sends zero when there are no setpoints; forwards a fresh setpoint; sends zero after the 0.3 s timeout;
- rejects NaN (which then times out) and infinity;
- the horizontal clamp keeps the direction; vertical and yaw rates are clamped; roll and pitch rates are zeroed;
- the sim's enable topic is published.
- **Catches:** a drone that keeps flying its last command when the software above it dies; a bad number reaching the motors; speeds above the limits.

**[test_state.py](seame-docker/ros2_ws/src/drone_fc_bridge/test/test_state.py) (7 cases):** runs with all noise set to 0, so the outputs are exact.
- velocity passes through;
- position is integrated from velocity, never copied from Gazebo (as on the real drone, which only has flow);
- body velocity is rotated by the heading; height and orientation come from the sim;
- the rangefinder reads level, longer when tilted, and `inf` out of range (REP 117).
- **Catches:** the sim cheating with perfect position; wrong frames; rangefinder geometry errors.

**[test_services.py](seame-docker/ros2_ws/src/drone_fc_bridge/test/test_services.py) (4 cases):** starts armed (default); disarms and re-arms through `fc/arm` (seen on `/X3/enable`); `fc/hold` sends zero despite setpoints; `fc/status` reports the setpoint age.

**[test_inav.py](seame-docker/ros2_ws/src/drone_fc_bridge/test/test_inav.py) (3 cases):** with `backend:=inav`, the stub for the real drone, the status says `inav` and disarmed, ROS can't arm it, and nothing reaches the sim's topics.
- **Catches:** ROS arming the real drone. Only the radio may.

**Why these help:** fc_bridge is the last software step before the motors. Its safety behaviour (timeout, clamps, NaN guard) is checked on every push, with the real compiled program.

### 5.6 fc_bridge's MSP library for the real drone: `test_msp.cpp` and `test_inav_decode.cpp` (37 cases, C++)

**What's being tested:** ROS-6 step A (João Barros, merged to `main` on Nov 11) added `fc_msp`, a small C++ library for fc_bridge's `inav` backend, so it can talk to the real drone:
- [msp.cpp](seame-docker/ros2_ws/src/drone_fc_bridge/src/msp.cpp) builds MSP v2 requests and finds the replies in the byte stream from the flight controller;
- [inav_decode.cpp](seame-docker/ros2_ws/src/drone_fc_bridge/src/inav_decode.cpp) turns nine INAV replies into SI units (m, m/s, V, A, W, rad).

It has no ROS and no network code, so it can be tested on its own. **It isn't used by `fc_bridge` yet**: the next step, ROS-6 step B, will connect it to the drone.

**How:** GoogleTest, registered with `ament_add_gtest` in fc_bridge's [CMakeLists.txt](seame-docker/ros2_ws/src/drone_fc_bridge/CMakeLists.txt). `colcon test` runs them in the `ros2-build-test` job like the other C++ tests. They read the four drone recordings from [drone_fc_bridge/test/data/](seame-docker/ros2_ws/src/drone_fc_bridge/test/data/), which are copies of the telemetry recordings, kept identical by `test_capture_copies.py` ([section 3.5](#35-test_capture_copiespy-the-c-tests-use-the-same-recordings-2-cases)). [capture.hpp](seame-docker/ros2_ws/src/drone_fc_bridge/test/capture.hpp) reads those files.

**[test_msp.cpp](seame-docker/ros2_ws/src/drone_fc_bridge/test/test_msp.cpp) (21 cases):**
- **Checksum:** CRC-8/DVB-S2 gives the standard check value, and matches the checksums in the recordings.
- **Requests:** the same bytes as `build_frame()` in the Python script. Only the nine read commands can be built: every write (such as `MSP_SET_RAW_RC`, which would fly the drone) and every other command in the whole command space is refused. A payload over the limit is refused.
- **Recordings:** every good reply parses; damaged replies are never returned. Each whole file, fed as one stream, gives every good reply in order, **plus a good reply hidden inside a damaged one**. The Python parser lost that one until [bug 1](#10-bugs-the-tests-have-found) was fixed.
- **Parser:** garbage between frames is skipped; a frame split at every possible byte still parses; our own requests echoed back are ignored; INAV's error reply (`$X!`) comes out as an error; a bad checksum is rejected; a header claiming 65 535 bytes doesn't hold back the replies behind it; the largest allowed payload is accepted; the buffer stays bounded on garbage; `reset()` drops a half frame; `skip_pending()` releases replies stuck behind a broken header (the damage seen in the recordings); a 2 MB backlog is read in linear time; the order is kept across partial reads.

**[test_inav_decode.cpp](seame-docker/ros2_ws/src/drone_fc_bridge/test/test_inav_decode.cpp) (16 cases):**
- **Identity:** API version, `INAV`, 9.1.0, from the recordings.
- **Rangefinder:** cm → m; −1 is out of range; 0 and other negatives are "no reading" (the Python script got 0 wrong until [bug 6](#10-bugs-the-tests-have-found) was fixed).
- **Attitude:** values from the recordings, and the limits (roll ±180°, pitch ±90°, heading 0–359°).
- **Status:** in every recording, the sensors present, never armed, and the reasons it can't arm (sensors calibrating, no radio link, no prearm, plus "not level" when tilted). A hand-built one: armed, with a rangefinder and a hardware failure. The simulator bits are not counted as reasons ([bug 5](#10-bugs-the-tests-have-found)).
- **Optical flow:** still and moving from the recordings; negative rates from a hand-built reply.
- **Battery:** all four recordings (16.16–16.31 V, 4 cells), and a hand-built reply with negative current and power ([bug 7](#10-bugs-the-tests-have-found)).
- **Local position:** none while disarmed on the bench; a hand-built reply pins the order of the six fields and their signs.
- **Every decoder** refuses any reply shorter than its layout, and accepts a longer one (newer firmware adds fields at the end).

**Errors they catch:** a wrong checksum; a parser that loses good replies after damage, or stalls behind a broken header; a request that could command the drone; signed fields read unsigned; wrong units or field order. João broke the code on purpose to check (wrong CRC, no resync, signed fields read unsigned), and each break made tests fail.

**Why they help:** this is the code that will read the real drone in flight. The recordings make it face the real Wi-Fi link's damage (replies cut short, old replies arriving late) before it ever flies.

**Limits:** nothing checks `fc_bridge` *using* the library yet. That comes with step B, ideally against a fake flight controller ([section 13](#13-what-isnt-tested-yet)). These files have no lint, because `drone_fc_bridge` has none ([section 8](#8-lint-and-style-checks)).

---

## 6. The whole ROS stack without Gazebo: `test_stack.py`

**Where:**
- [seame-docker/ros2_ws/src/drone_bringup/test/test_stack.py](seame-docker/ros2_ws/src/drone_bringup/test/test_stack.py) and its helper [fake_drone.py](seame-docker/ros2_ws/src/drone_bringup/test/fake_drone.py).
- Registered in drone_bringup's `CMakeLists.txt` with `add_launch_test` (180 s limit, domain 198), so it runs on every push.

**How:**

```
  test: actions ---> mission --cmd/mission--> safety_manager --> fc_bridge --> fake_drone
                       ^                          ^                  |  ^          |
  test: radio ---------|--------- cmd/radio ------+                  |  +- /X3/odom+
                       +------------ fc/range, fc/odom, fc/status ---+
```

- The three real nodes (mission, safety_manager, fc_bridge) start exactly as `sim.launch.py` starts them, with `sim.yaml`.
- `fake_drone.py` replaces Gazebo, in its own process like Gazebo. It flies at whatever speed fc_bridge commands; disarmed in the air, it drops. It publishes `/X3/odom`, the true pose.
- The test sends real `Takeoff`, `Goto` and `Land` actions, plays the radio on `cmd/radio`, and disarms through `fc/arm` as the arm switch would.

**What it checks (5 cases):**

| Test | Checks |
| --- | --- |
| `test_takeoff_refused_until_armed` | Like the real drone, only the radio arms: Takeoff is refused and the drone stays on the ground. |
| `test_full_flight` | Takeoff reaches `target_h`. 1 m forward really moves 1 m. Turn 90° left, then 1 m forward, goes to the old left (body frame to world). Asking for 2 m/s still arrives. Land. No command ever exceeded the `sim.yaml` limits. |
| `test_radio_takes_over_and_gives_back` | The radio takes control mid-Goto: the Goto is aborted ("overridden"), the mission goes silent, new goals are refused, and the drone follows the sticks. When the sticks go quiet, the mission holds where the radio left it, then lands. |
| `test_disarm_mid_flight` | The kill switch mid-Goto: the Goto is aborted ("disarmed"), the drone drops, the mission goes silent, and Takeoff is refused. |
| `test_disarm_while_the_radio_flies` | The kill switch while the radio has control: the drone drops, and once control comes back the mission stays silent instead of holding a height (and climbing when re-armed). Skipped until [bug 2](#10-bugs-the-tests-have-found) was fixed. |

**Errors it catches:** nodes that each pass their own tests but don't work together: wrong topic names or remaps, QoS mismatches, wrong frames, a broken handover between the radio and the mission, and limits that differ between nodes.

**Why it helps:** it's the closest thing to a real flight that runs on every PR, in about a minute, without Gazebo.

**Was flaky, fixed on Nov 12.** It had two causes: [bug 3](#10-bugs-the-tests-have-found) in the mission, and [bug 8](#10-bugs-the-tests-have-found) in this test (its own node on a multi-threaded executor starved the radio stick player). Measured in the dev container, 6 runs each:

| Mission | Test node | Passed |
| --- | --- | --- |
| before the fix | multi-threaded | 3 of 6 |
| fixed | multi-threaded | 3 of 6 |
| before the fix | single-threaded | 5 of 6 |
| fixed | single-threaded | **6 of 6** |

---

## 7. Flight in Gazebo, nightly: `test_sim_flight.py`

**Where:**
- The test: [seame-docker/ros2_ws/src/drone_bringup/test/test_sim_flight.py](seame-docker/ros2_ws/src/drone_bringup/test/test_sim_flight.py). Not registered in CMake, so `colcon test` doesn't run it.
- The runner: [seame-docker/scripts/sim_flight_test.sh](seame-docker/scripts/sim_flight_test.sh), on the host. It starts a throwaway container from the dev image, with no display and no GPU like GitHub's machines, builds, and runs the test.
- CI: [.github/workflows/nightly.yml](.github/workflows/nightly.yml).
- It needs the `headless:=true` option of `sim.launch.py`, which runs Gazebo's server only (`gz sim -s`) with no window.

**How:**
- It starts `sim.launch.py headless:=true radio:=false`. With no radio, the mission arms on Takeoff and disarms after Land.
- It flies one flight step by step, checking everything against **Gazebo's ground truth** (`/sim/ground_truth`), not the drone's own estimate.
- After a failed step, the rest are skipped, because they share one flight.
- At the end it stops its own Gazebo. Otherwise Gazebo would outlive the test and block the next run.

| Step | Checks | Pass if | Measured |
| --- | --- | --- | --- |
| `test_1_sim_comes_up` | ground truth, `fc/status`, `fc/range`, the action servers, sim time | all within 180 s (the first run downloads the X3 model from Fuel); backend `sim` | about 3 s |
| `test_2_on_the_ground_at_start` | on the ground, still, upright | height and `fc/range` < `ground_h` | z 0.054 m |
| `test_3_takeoff` | `Takeoff` to `target_h` | succeeds; true height and rangefinder 1.2 ± 0.1 m | 1.16–1.19 m |
| `test_4_hover_drift` | 3 s to settle, then hover 10 s | no overshoot above 1.3 m; drift < 0.1 m; height 1.2 ± 0.05 m | drift 0.000 m, 1.196–1.204 m |
| `test_5_square` | the demo's square: 1 m forward, then a quarter turn left, 4 times | sides 1 ± (`pos_tolerance` + 0.1) m; turns 90° ± (`yaw_tolerance` + 0.02); closes < 0.3 m | sides 0.87–0.94 m, turns 88–91°, closes 0.085 m |
| `test_6_speed_capped_at_the_limit` | a Goto asking for 2 m/s, and all speeds since takeoff | reaches > 80 % of `max_speed_xy` but never more than the limit + 10 %; same for vertical speed and yaw rate; fc_bridge never sends over a limit | 0.459 m/s; vertical 0.300 m/s |
| `test_7_land` | `Land` | succeeds; back on the ground; upright; the mission disarms | z 0.055 m |
| `test_8_mission_dies_and_the_drone_stops` | take off, kill the mission node mid-Goto (SIGKILL), land by hand on `cmd/manual`, disarm | stopped (< 0.05 m/s) within `setpoint_timeout_s` + 1 s; coasts < 0.5 m; holds height; lands | 1.07 s, 0.228 m |

The "measured" column comes from a passing run with bug 3 fixed. Tolerances are taken from `sim.yaml`, so they follow the config.

**Output:** see [section 11](#11-how-to-run-the-tests).

**Errors it catches:** what the faster tests can't see:
- the launch file and Gazebo bridge not working together;
- real flight dynamics (overshoot, braking, drift);
- speeds above the limits in actual flight;
- a drone that keeps flying when the mission program crashes.

**Why nightly and not on every push:** it builds the image, starts Gazebo and flies for about 2 minutes. That's too slow and heavy for every push, and it isn't a check every PR has to pass.

**Was a known problem, fixed on Nov 12:** before [bug 3](#10-bugs-the-tests-have-found) was fixed, it failed at the square on most runs. With the fix, the whole flight passed (`scripts/sim_flight_test.sh`, Nov 12).

---

## 8. Lint and style checks

These read the code without running it. They come from the ROS package templates (`test_*.py` files in Python packages) and from `ament_lint_auto` (CMake packages). The ROS packages have 33 such cases.

| Check | What it looks at | Packages | Catches |
| --- | --- | --- | --- |
| flake8 | Python style and simple bugs: unused imports, undefined names, line length 99, quote style, import order | all Python packages, and drone_bringup's Python files | typos in names, dead code, inconsistent style |
| pep257 | docstring rules (summary line ending with a period, imperative mood, and so on) | same | missing or badly formed docstrings |
| mypy | type checking | drone_basics_py, drone_mission, drone_safety | passing the wrong type, `None` where a number is expected |
| xmllint | `package.xml` against the ROS schema | drone_basics_py, drone_mission, drone_safety, drone_bringup, drone_basics_cpp | invalid package files that break `rosdep` or the build |
| lint_cmake | `CMakeLists.txt` style | drone_bringup, drone_basics_cpp | malformed CMake |
| uncrustify | C++ formatting | drone_basics_cpp | inconsistent C++ style |
| cppcheck | C++ static analysis | drone_basics_cpp | **skipped** (cppcheck 2.13 performance issue) |
| copyright | license headers | Python packages (skipped); turned off in the CMake packages | nothing yet: no license headers in the code |

For `telemetry/`, the CI job runs `py_compile` (the file parses as Python) and `flake8 --max-line-length=140`.

**Gaps:** `drone_fc_bridge` has no lint at all: its `CMakeLists.txt` doesn't call `ament_lint_auto`. With ROS-6 step A it now has five C++ files without lint. Turning it on was measured on Nov 12: uncrustify wants 42 lines reformatted (in `fc_bridge.cpp` and `test_inav_decode.cpp`, fixed automatically with `ament_uncrustify --reformat`), and cpplint finds two small things (a missing newline at the end of `fc_bridge.cpp`, a comment without a space). cppcheck is skipped, so no C++ static analysis runs anywhere.

---

## 9. Docker image build

The `docker-image` job in `ci.yml` builds [seame-docker/Dockerfile](seame-docker/Dockerfile) from scratch, without pushing it. **It catches** a Dockerfile that no longer builds, such as a package renamed or removed from apt. That would otherwise only be found when someone sets up a new laptop. Its layer cache is also reused by the nightly.

---

## 10. Bugs the tests have found

An **expected fail** is a test marked `xfail(strict=True)`. It shows a known bug without turning CI red. "Strict" means that once someone fixes the bug, the test starts passing, which pytest reports as an error. That's the reminder to remove the mark. No test is marked that way now: bugs 1, 2, 5, 6 and 7 had one, and since their fixes (Nov 12) those tests just pass.

| # | Bug | Where | Found by | Effect | Status |
| --- | --- | --- | --- | --- | --- |
| 1 | After a reply with a bad checksum, the parser throws away the whole length that broken header claimed, including any good replies inside it. | `telemetry/inav_telemetry.py`, `_next_frame` | `test_msp_frame.py`, `test_valid_reply_inside_a_corrupt_one_is_recovered` (real damaged frame from `radio_off`) | Lost telemetry replies on a noisy link; `MSP_BOXNAMES` needs retries. | **Fixed** (Nov 12): on a bad checksum it drops only the `$X` and searches again, like fc_bridge's C++ parser (`Captures.RecoversFrameEmbeddedInDamagedOne` in `test_msp.cpp`). Still open: a reply right after a damaged header waits until the bytes that header claims have arrived; fc_bridge gives up on it at the reply timeout (`skip_pending()`), the script doesn't yet. |
| 2 | Disarming while the radio has control is ignored. If control comes back while the drone is still falling, the mission goes to "hold" and keeps commanding a climb, disarmed on the ground. Re-armed, **it climbs by itself with no Takeoff**. | `drone_mission/logic.py`, `on_armed` and `set_control` | `test_stack.py`, then proven in `test_logic.py` | Unsafe: an unexpected climb after re-arming. | **Fixed** (Nov 12): when control comes back, `set_control` grounds a drone known to be disarmed instead of holding. Both tests run and pass. |
| 3 | The mission's commands stall for 0.3–0.8 s at a time. rclpy's multi-threaded executor misses its 20 Hz timer, so fc_bridge times out and sends zero, and goals abort with "rangefinder lost". | `drone_mission/mission.py` (`MultiThreadedExecutor`) | `test_stack.py` and `test_sim_flight.py` | Jerky flight in the Gazebo sim too ("Setpoint timeout" every 1–2 s). `test_stack.py` failed about 4 runs in 10; the nightly failed at the square. | **Fixed** (Nov 12): a single-threaded executor, and `execute()` awaits the next tick instead of sleeping. `test_stack.py` passed 6 out of 6 (with bug 8 fixed too), and the whole Gazebo flight passed. |
| 4 | `flow_model` prints a `KeyboardInterrupt` traceback every time the sim shuts down. | `drone_sim_sensors/flow_model.py`, `main()` | `test_sim_flight.py` logs | Cosmetic. | Open. One-line fix: catch `KeyboardInterrupt`. |
| 5 | The simulator-mode bits (4, 5) and unused bits are listed as reasons arming is blocked. | `telemetry/inav_telemetry.py`, `arming_fields` | Found while writing fc_bridge's C++ decoders (ROS-6 step A); now `test_decoders.py` | On INAV SITL every status would say it can't arm because it's a simulator. | **Fixed** (Nov 12): only bits 6–16 and 18–30 are listed (`ARMING_BLOCKER_BITS`). |
| 6 | 0 cm from the rangefinder is reported as a valid 0.0 m. INAV sends 0 when no rangefinder is running. | `telemetry/inav_telemetry.py`, `d_rangefinder` | Same; `test_decoders.py` | Telemetry shows the drone "at 0.00 m" with no sensor at all. | **Fixed** (Nov 12): 0 is reported as not valid. |
| 7 | Power, mAh drawn and mWh drawn are read unsigned. | `telemetry/inav_telemetry.py`, `d_inav_analog` | Same; `test_decoders.py` | A negative current shows about 42 949 kW. | **Fixed** (Nov 12): unpacked as signed, `'<BHhiiiIBH'`. |
| 8 | `test_stack.py`'s own node spun a multi-threaded executor, which starved its radio stick player (`play_radio`) for more than `source_timeout_s` (0.3 s). safety_manager then gave control back to the mission in the middle of a takeover. | `drone_bringup/test/test_stack.py` | Its failing runs' logs: extra `Active source: radio` and `overridden -> hold` changes during the radio test | The radio test failed with "mission kept publishing under the radio". A failure there while the radio had control then hit bug 2, so the next test failed too. | **Fixed** (Nov 12): a single-threaded executor in the test too. |

---

## 11. How to run the tests

All ROS commands run **inside the dev container** (`cd seame-docker && docker compose exec dev bash`), from `~/ros2_ws`, after `source /opt/ros/jazzy/setup.bash`.

### Everything, the way CI does it
```bash
# on the host, in seame-docker/
./scripts/run_tests.sh
```
This does a clean build and runs every ROS test plus lint, in `/tmp` inside the container, so your own `build/` is left alone. It writes `report.md`, `results.json` and a line in `history.csv` under `seame-docker/logs/tests/<date>_<commit>/`. Run it before pushing. It doesn't include the telemetry tests or the Gazebo flight.

### One ROS package
```bash
colcon build --packages-up-to drone_bringup && source install/setup.bash
colcon test --packages-select drone_bringup
colcon test-result --verbose          # every failure, with file and line
```

### One file, quickly
```bash
# plain pytest files (no build needed: they read from src/)
python3 -m pytest src/drone_bringup/test/test_config.py -v
# these two need the build (source install/setup.bash): they look up installed files
python3 -m pytest src/drone_bringup/test/test_launch_files.py src/drone_bringup/test/test_worlds.py -v -rs
cd src/drone_mission && python3 -m pytest test/test_logic.py -v     # 44 passed

# C++ tests (need the build): through colcon, or run the program directly
colcon test --packages-select drone_fc_bridge --ctest-args -R 'test_msp|test_inav_decode'
./build/drone_fc_bridge/test_msp --gtest_filter='Parser.*'          # one group, verbose

# launch tests (need the build): set the domain like CMakeLists.txt does
export ROS_DOMAIN_ID=198 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST
launch_test src/drone_bringup/test/test_stack.py                    # about 60 s
```
`test_stack.py` reads `sim.yaml` from `install/`. If you aren't using `--symlink-install`, rebuild drone_bringup after editing `sim.yaml`.

### Telemetry tests
`telemetry/` isn't mounted in the dev container, so copy it in, from the host, in the repo root:
```bash
docker exec seame-dev rm -rf /tmp/tele          # otherwise docker cp nests it
docker cp telemetry seame-dev:/tmp/tele
docker exec -w /tmp seame-dev python3 -m pytest tele -v
docker exec -w /tmp seame-dev python3 -m flake8 --select=E,W,F --max-line-length=140 tele
```
Expected: 139 passed, 1 skipped, and no lint output. The skip is the copies check in `test_capture_copies.py`: in `/tmp/tele` there's no `ros2_ws` next to it. On the host, from the repo root (`python3 -m pytest telemetry -v`, needs pytest), it runs: 140 passed. `--select=E,W,F` makes the container's flake8, which has extra plugins, match CI's plain flake8.

### Gazebo flight
```bash
# on the host, in seame-docker/  (a fresh container; your own sim can stay open)
./scripts/sim_flight_test.sh                    # about 2 min
```
It prints what each step measured and **OK** or **FAILED**. The files go to `ros2_ws/log/sim_flight/<date>/`, which git ignores:

| File | Contents |
| --- | --- |
| `flight.log` | the full test output |
| `flight.xml` | xUnit report |
| `flight_bag/` | rosbag of the flight; replay it with `ros2 bag play flight_bag` |
| `ros_log/` | each node's log |
| `build.log` | colcon build output |

On GitHub, the same files are in the `sim-flight` artifact of each nightly run.

To **watch** the test fly, run it by hand in the dev container and open Gazebo's window on it:
```bash
export ROS_DOMAIN_ID=196 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST GZ_PARTITION=flight_test
launch_test src/drone_bringup/test/test_sim_flight.py
# second terminal, once it has started:
GZ_PARTITION=flight_test gz sim -g
```

Running the sim by hand without a window (`ros2 launch drone_bringup sim.launch.py headless:=true radio:=false`) is **not** a test: nothing is checked until you send goals yourself. Spell it `headless`: ROS silently ignores a misspelled argument and opens the window anyway.

---

## 12. How to add a test

- **Python ROS package** (`drone_mission`, `drone_safety`, `drone_basics_py`, `drone_sim_sensors`): add `test/test_<something>.py`. `colcon test` finds it automatically, and flake8, pep257 and mypy apply to it.
- **CMake package** (`drone_bringup`, `drone_fc_bridge`): add the file, then register it in `CMakeLists.txt` inside `if(BUILD_TESTING)`:
  ```cmake
  ament_add_pytest_test(test_name test/test_name.py TIMEOUT 30)      # plain pytest
  find_package(launch_testing_ament_cmake REQUIRED)
  add_launch_test(test/test_name.py TIMEOUT 120
    ENV ROS_DOMAIN_ID=<unused number> ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)   # starts nodes
  ```
  Add every package the test imports or starts as a `<test_depend>` in `package.xml`. CI installs only build and test dependencies.
- **Telemetry:** add `telemetry/tests/test_<something>.py`; `conftest.py` makes `inav_telemetry` importable.
- **Something slow or needing Gazebo:** don't register it with colcon. Add a step to `test_sim_flight.py`, or a new file run by `scripts/sim_flight_test.sh`.
- **A known bug you can't fix now:** write the test anyway and mark it `@pytest.mark.xfail(strict=True, reason="...")`. In a launch test, use `@unittest.skip("...")` instead: launch_testing reports `expectedFailure` as a failure.
- Run `./scripts/run_tests.sh` (and the telemetry tests) before pushing.

---

## 13. What isn't tested yet

**No tests at all:**
- `drone_interfaces` (message and action definitions only);
- `demo_flight`, `setpoint_pub` and `drone_basics_cpp`'s `watchdog`;
- `joy_node` with the real radio.

**Partly tested:**
- fc_bridge's `inav` backend is still a stub ("MSP not implemented yet"), so the tests only check that it refuses to arm and stays away from the sim. The MSP library it will use is tested on its own ([section 5.6](#56-fc_bridges-msp-library-for-the-real-drone-test_mspcpp-and-test_inav_decodecpp-37-cases-c)), but isn't connected yet.
- `drone_fc_bridge` has no lint, and cppcheck is skipped.
- `sim.launch.py`: what it starts is checked (section 4.2), but the nodes only run together in `test_stack.py` and the nightly.
- The worlds: checked as files (section 4.3), but only the default world is flown, by the nightly.

**Planned** (details in [docs/CI_Tests.md](docs/CI_Tests.md)):

| Item | Idea |
| --- | --- |
| A5 | Run INAV's own firmware as a Linux program (SITL) every night and point `inav_telemetry.py` at it. Most useful at the next INAV upgrade, and once fc_bridge talks MSP. In SITL, optical flow and rangefinder reply with zeros. |
| A6 | A bench script that runs the recording checks live against the real drone. |
| B2 | fc_bridge tested with the real `sim.yaml` settings. |
| D2 | The flight test in every world, once `feature/153` is merged (a list of worlds in `nightly.yml`). |
| D3 | Fake radio input in the full sim. |
| — | A flight step that checks optical flow against Gazebo's speed ÷ height, using the maths of `flow_check.py` (branch `test`). |
| — | A fake flight controller: a TCP server that answers MSP with the recorded replies, for `inav_telemetry.py` now and fc_bridge's `inav` backend later. |
| E2 | Lint for `drone_fc_bridge`: about 42 lines to reformat automatically, plus two small fixes. |

**Checked by hand instead.** These need the real drone, the radio, or a person watching Gazebo, so CI can't run them. The steps are in the documents below, and the **date and result of the last run are kept in [docs/TESTS.md](docs/TESTS.md)** (update its row when you redo one), not copied here.

| Area | Check | What it shows | How |
| --- | --- | --- | --- |
| Sim | Velocity frame (`source:=circle`), circle flight, mission demo (`demo:=true`) | Commands are in the body frame; the circle's radius and lap time; every goal of the demo succeeds at the right height | [SIM_TELEOP.md](seame-docker/SIM_TELEOP.md), "Try it" |
| Sim | Radio takeover, with `ros2 topic pub` and with the real RadioMaster Pocket | The radio interrupts a Goto; releasing it goes to hold; re-arm and fly after a Land | same |
| Sim | Arming in the sim, `backend:=inav` launch, which nodes each launch argument starts | Takeoff refused until armed; arm switch off in the air disarms; no Gazebo with `inav` | same. The launch arguments are now also checked automatically ([section 4.2](#42-what-the-launch-file-starts-test_launch_filespy-24-cases)). |
| Sim | Arm switch bounce (`tools/arm_bounce.py`), odometry rate | The switch bounces 0–35 ms (fixed with `arm_hold_s`); odometry at 50 Hz | same |
| Link | Wi-Fi round trip (`wifi_rtt`) | Lost replies, median/p90/p99/max round trip and jitter through the ESP | [measure_wifi_rtt.py](seame-docker/logs/measurements/measure_wifi_rtt.py), results in `seame-docker/logs/measurements/wifi_rtt/` |
| Link | Every MSP message answers | Each message on the list gets a reply from INAV 9.1.0, and how many don't | `python3 telemetry/inav_telemetry.py`, see [telemetry/README.md](telemetry/README.md) |
| Link | MSP rate and loss per message (INAV-4, #126) | Replies per second and stalls, per message | `msp_inventory.py rate`, see [the captures README](telemetry/inav/captures/README.md) |
| Drone | Arming: kill switch, PREARM timeout, arm switch on at power-up; radio-loss failsafe; each motor's position and direction | The drone arms only when it should, drops on radio loss, and the motors match INAV's layout | [docs/ELRS_Guide.md](docs/ELRS_Guide.md) |
| Drone | Battery voltage reading | INAV's voltage against the charger and a multimeter (`vbat_scale`) | [docs/Li-Po_Battery_Tests.md](docs/Li-Po_Battery_Tests.md) |

The Wi-Fi link checks (bench rules: props off, nothing armed) are the ones that matter most for fc_bridge's `inav` backend, because they measure the link it will use.

**Tools that are not tests** (run by hand, nothing passes or fails):

| Tool | What it does |
| --- | --- |
| [telemetry/latency_test.py](telemetry/latency_test.py) | measures the round-trip delay to the flight controller through the ESP, and saves a CSV |
| [telemetry/inav/captures/msp_inventory.py](telemetry/inav/captures/msp_inventory.py) | records the MSP captures, and measures message rates |
| [seame-docker/scripts/smoke_test.sh](seame-docker/scripts/smoke_test.sh) | opens terminals running `setpoint_pub`, the watchdog and `ros2 topic hz`, to check by eye |

---

## 14. Words used in this file

| Word | Meaning |
| --- | --- |
| **MSP** | MultiWii Serial Protocol, how programs talk to the INAV flight controller. We use version 2. |
| **CRC / checksum** | A number computed from a frame's bytes; if a byte changes on the way, it no longer matches. MSP v2 uses CRC-8/DVB-S2. |
| **Decoder** | A function that turns a reply's raw bytes into numbers with units. |
| **Capture / recording** | Real replies from the drone, saved to a file and replayed in tests. |
| **Launch test** | A test that starts real ROS nodes (`launch_testing`) and talks to them from a test node. |
| **Ground truth** | Where Gazebo says the drone really is; the drone itself only has its own estimate. |
| **Headless** | Gazebo running with no window (`gz sim -s`), as on CI machines with no screen. |
| **Expected fail (xfail)** | A test that shows a known bug without turning CI red; with `strict=True` it flags the day the bug is fixed. |
| **Artifact** | Files a GitHub workflow run keeps for download, such as logs and reports. |
| **SITL** | Software in the loop: INAV's firmware compiled to run on a PC. |
