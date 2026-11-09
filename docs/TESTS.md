---
title: Tests we run
---
# Tests we run

Every test and check the team runs, how to run it, and where its last result is. The details stay where they were written; this page points to them.

**Last results:** automated tests and measurements keep their own record in `logs/` (one dated folder per run, plus a `history.csv`), so this page links to that record instead of copying numbers that go stale. Checks done by hand have no record of their own, so their date and result are written here. **When you redo one, update its row.**

## At a glance

| Area | Test | How | Last result |
| --- | --- | --- | --- |
| ROS | Unit, launch and lint tests (123 cases) | `./scripts/run_tests.sh` | [logs/tests/history.csv](../seame-docker/logs/tests/history.csv) |
| CI | Build + test, telemetry lint, Docker image | automatic on push and PR | GitHub → Actions |
| Sim | Flights, takeover, failsafes, by hand | [SIM_TELEOP.md](../seame-docker/SIM_TELEOP.md) | [below](#sim-by-hand) |
| Link | Wi-Fi round trip (`wifi_rtt`) | `logs/measurements/measure_wifi_rtt.py` | not run on the drone yet |
| Link | MSP messages answer (`inav_telemetry.py`) | [telemetry/README.md](../telemetry/README.md) | Nov 8, all answer, ~3% no reply |
| Link | MSP rate and loss per message (INAV-4, #126) | coming | — |
| Drone | Arming and radio-loss failsafe | [ELRS_Guide.md](./ELRS_Guide.md) | passed; on hold (motor wire) |
| Drone | Battery voltage reading (`vbat_scale`) | [Li-Po_Battery_Tests.md](./Li-Po_Battery_Tests.md) | Oct 28, set to 1103 |

## ROS: automated tests

**Run all of them and keep the result** (host, in `seame-docker/`, dev container running, about 1.5 min):

```bash
./scripts/run_tests.sh
```

A clean build and `colcon test` with CI's commands. Each run gets `logs/tests/<date>_<commit>/` with a readable `report.md` (verdict, failures, what changed since the previous run) and a line in `history.csv`. See [logs/README.md](../seame-docker/logs/README.md).

**Quick check while working** (inside the container, no record kept):

```bash
cd ~/ros2_ws && colcon build && colcon test --packages-select drone_fc_bridge drone_basics_py drone_mission drone_safety && colcon test-result --verbose
```

| Package | Behaviour tests | Cases |
| --- | --- | --- |
| `drone_fc_bridge` | `test_failsafes` (timeout, NaN/inf, clamps), `test_state` (odometry, range), `test_services` (arm, hold, status), `test_inav` (the `inav` backend refuses to arm, publishes nothing to Gazebo) | 23 |
| `drone_mission` | `test_logic`: whole flights against a toy drone (takeoff, goto, land, range lost, overrides, arming) | 43 |
| `drone_basics_py` | `test_radio_teleop`: arm switch, takeover, bounce, stick scaling | 24 |
| `drone_safety` | `test_arbiter`: which source commands the drone | 9 |

What each file checks, case by case: the **Tests** table in [seame-docker/README.md](../seame-docker/README.md#tests).

The other 24 cases are lint and style checks (flake8, pep257, mypy, xmllint, copyright, cppcheck, uncrustify, lint_cmake). Four are skipped on purpose: the copyright check in three Python packages (no license header yet) and cppcheck on `watchdog.cpp` (too slow in cppcheck 2.13).

**Are the tests real?** Each guard was broken on purpose once to see its tests fail (timeout, debounce, altitude hold, priority order, arming checks, `inav` refusing `fc/arm`). Dates and counts are in the "Checked" lines of [CHANGES.md](../seame-docker/CHANGES.md).

## CI

[.github/workflows/ci.yml](../.github/workflows/ci.yml) runs on pushes and pull requests to `main`, `Develop`, `test` and `ci/**`, or by hand (Actions → CI → Run workflow). **Not on `staging`**: run `run_tests.sh` there before merging.

| Job | What it checks |
| --- | --- |
| `ros2-build-test` | Builds `seame-docker/ros2_ws` on a clean `ros:jazzy` image and runs `colcon test`; the result files are uploaded as `ros2-test-results` |
| `telemetry-python` | `telemetry/*.py` compiles and passes flake8 (lines up to 140) |
| `docker-image` | The dev container still builds from scratch |
| `block-red-pr` | If any job fails on a PR, the PR goes back to draft with a comment, so it can't be merged by accident |

Results: the PR's checks, or the repo's **Actions** tab.

## Sim, by hand

Steps for each are in [SIM_TELEOP.md](../seame-docker/SIM_TELEOP.md) ("Try it"). Results from SIM_TELEOP's Results table and CHANGES.md.

| Check | Last run | Result |
| --- | --- | --- |
| Velocity frame (`source:=circle`) | Oct 22–23 | Body frame: forward follows the nose |
| Circle flight | Oct 22–23 | Radius ~0.545 m for 0.6 commanded, lap 12.5 s |
| Mission demo (`demo:=true`) | Oct 29 | Every goal succeeded; 1.19–1.22 m through eight Gotos; square sides 0.82–0.91 m for 1.0; disarmed after landing |
| Radio takeover (`ros2 topic pub` on `/cmd/radio`) | Oct 30 | Took over mid-Goto, Goto aborted; `mission` held and landed after |
| Radio takeover with the real Pocket (section 1c) | Oct 30 | Takeover mid-Goto, release to hold, re-arm and fly after Land |
| Arming in the sim (fake Pocket) | Oct 30 | Takeoff refused until armed; SA off in the air disarms and drops |
| `backend:=inav` launch | Oct 30 | No Gazebo, `fc/status` disarmed, `fc/arm` refused |
| Launch arguments (which nodes start) | Nov 3 | `demo:=true` gates every scripted flight; plain launch flies nothing |
| Arm switch bounce (`tools/arm_bounce.py`) | Oct 26 | Bounce confirmed (bursts 0–35 ms); fixed with `arm_hold_s` 0.1 s |
| Odometry rate | Oct 22–23 | 50.0 Hz |

`scripts/smoke_test.sh` opens `setpoint_pub`, the `watchdog` and `ros2 topic hz /setpoint_velocity` in tabs, to see the basics run; it reports nothing by itself.

## Link to the drone (real hardware)

Bench rules for all of these: props off, battery in, nothing armed.

**Wi-Fi round trip** (STK-5), recorded in `logs/measurements/wifi_rtt/`. In `seame-docker/`, on the drone's network:

```bash
python3 logs/measurements/measure_wifi_rtt.py --note "bench, AP mode, from the Pi, radio on" -n 1000 --interval 0.03
```

It runs [telemetry/latency_test.py](../telemetry/latency_test.py) and records lost replies, median/p90/p99/max round trip, jitter and the real request rate. Say where, which machine and which ESP mode in `--note`. Last result: [wifi_rtt/history.csv](../seame-docker/logs/measurements/wifi_rtt/history.csv) (none yet).

**MSP messages answer:** `python3 telemetry/inav_telemetry.py` ([how](../telemetry/README.md)). Last run Nov 8 (INAV-4): every message on the candidate list answered on INAV 9.1.0, 4 of 143 requests without a reply (about 3%), drone upside down, no radio.

**MSP rate and loss per message** (INAV-4, #126): coming; its results will go in `logs/measurements/msp_rates/`.

## Drone hardware

| Check | Where | Last result |
| --- | --- | --- |
| Arming: kill switch, PREARM timeout, arm switch on at power-up | [ELRS_Guide.md](./ELRS_Guide.md) ("Arming successful tests") | All passed. Arming tests on hold since a damaged motor wire was found |
| Radio-loss failsafe (DROP after 0.5 s, stays disarmed) | [ELRS_Guide.md](./ELRS_Guide.md) | Passed |
| Each motor's position and direction (props off) | [ELRS_Guide.md](./ELRS_Guide.md) ("Motor setup") | All four match INAV's diagram |
| Battery voltage: INAV vs charger vs multimeter | [Li-Po_Battery_Tests.md](./Li-Po_Battery_Tests.md) | Oct 28: `vbat_scale` set to 1103; INAV then within 0.01 V of the charger and multimeter average |

## Not tested yet

- `wifi_rtt` on the real drone (INAV-4 is running it).
- Command rate and jitter in the sim (ROS-7.1, #77).
- The `inav` backend reading the real drone: tests come with the backend.
- The MTF-02P (not fitted yet).

# Tags

#guides
#resources
