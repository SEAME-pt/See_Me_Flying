# See Me Flying: presenter guide

**Deck:** See Me Flying · Week 1 & M1 Plan (9 slides)
**Total time:** about 12 minutes + questions
**Goal of the talk:** show what we did in week 1, how the drone system fits together, and agree on how we tackle Milestone 1.

---

## 1 · Cover (30 s)

- "We're the drone team. Our platform is the Pilotix Brook 2.5", a small indoor drone."
- "Milestone 1 runs from 19 October to 11 December: 8 weeks."
- "Today: what we did last week, how the system works, and our plan."

## 2 · Agenda (20 s)

- Read the list quickly. Don't explain anything yet.

## 3 · The platform (1.5 min)

- Point at the table: these are the parts on our drone.
- **Main message (the dark box):** the drone is too small to carry a computer.
  - All the "thinking" (perception, planning) runs on a ground PC.
  - Commands fly to the drone over Wi-Fi.
- "So latency and losing the link are design problems from day one, not edge cases."

## 4 · What we did last week (1.5 min)

Let one person from each workstream say one sentence, or say it for them:

- **Hardware:** first wiring plan for camera, Wi-Fi module, optical flow and LEDs.
- **ROS 2 + INAV:** a shared Docker dev environment (ROS 2 Jazzy), plus a first test: one node sends speed commands, another warns if they stop.
- **System design:** mapped the drone onto the course's layered architecture, drew the system diagram, split the milestone into 4 sprints.

> ⚠️ Fill in or remove the bracketed item "[Bench power-up / ELRS bind status]" before presenting.

## 5 · Hardware wiring plan (1 min)

- "This is the first draft of how everything connects to the flight controller."
- **Say clearly that it's a draft.** Before anyone solders, we check it against the real flight controller pinout.
- Known gaps to mention:
  - The radio receiver (kill switch) isn't drawn yet.
  - The drawing and the "Connections Summary" box don't fully match.

## 6 · ROS 2 today, INAV next (1.5 min)

- **Left box = what exists in our repo today.**
  - A Docker setup so everyone has the same environment.
  - Two test nodes: `setpoint_pub` sends speed commands, `watchdog` warns if they stop.
- **Right box = what we still have to build.**
  - `flight_interface` is the translator between our ROS 2 code and the flight controller (INAV).
  - It talks to the drone with MSP messages over Wi-Fi.
- **Open question:** how INAV accepts commands from outside (probably "RC override"). We test this in Sprint 1.

## 7 · System design (2 min)

Walk the diagram **left to right**:

1. **Drone (left):** the flight controller runs INAV, which keeps the drone stable. It reads the optical flow sensor and drives the motors.
2. **Middle:**
   - The safety pilot holds the radio.
   - Wi-Fi carries commands.
   - The 5.8 GHz link carries video.
3. **Ground PC (right):**
   - `mission` decides what to do.
   - `flight_interface` turns that into commands.
   - `perception` uses the video.

Key points:
- **Three paths:** commands (Wi-Fi), video (5.8 GHz), safety (radio).
- **The kill switch never goes through ROS 2 or Wi-Fi.** If our code crashes, the human can still stop the drone.
- Dashed boxes = not built yet.

## 8 · How we work (1.5 min)

- **Top row:** every task is a GitHub issue. Each issue goes through branch → pull request → CI green → review → merge.
- **Cards:** four automatic checks (pipelines). Each one runs only when its part of the repo changes.
  - `hil` tests on the real drone on the bench, props off.
- **Bottom:** our team rules.
  - **"Done"** means CI green, tests added, and the owner approved.
  - **Build sheriff:** one person per week makes sure `main` stays green.

## 9 · Four sprints (1.5 min)

- "Four sprints of two weeks. Each one ends with a demo."
- One line per sprint:
  - **S1:** basics working
  - **S2:** the translator node
  - **S3:** safety
  - **S4:** prove it on the real drone
- **Say it's a proposal:** "Does this order make sense to everyone?"

## Close (1 min): decide before leaving the room

- [ ] Clean up the duplicated GitHub issues (#3–#6 vs #8–#11) and give every issue one owner
- [ ] Agree on the sprint plan
- [ ] Pick our demo day
- [ ] Ground computer: laptop or Raspberry Pi 5 + Hailo?

---

## Quick answers for questions

| If someone asks… | Short answer |
|---|---|
| Why not put a computer on the drone? | Too small and too light: a 2.5" drone can't carry one. Everything smart runs on the ground. |
| What is INAV? | The firmware on the flight controller. It keeps the drone stable; we only send it commands. |
| What is MSP? | INAV's message protocol. We use it over Wi-Fi to read telemetry and send commands. |
| What is `flight_interface`? | Our ROS 2 node that translates our commands into MSP for INAV. Not built yet. |
| Why PX4 in simulation if the drone runs INAV? | The course uses PX4 SITL in Gazebo. Our job is to hide the difference behind one interface and measure the gap. |
| What is HIL? | Hardware-in-the-loop: automatic tests against the real flight controller on the bench, props off. |
| What happens if Wi-Fi drops? | Our watchdog commands hover or land, and INAV's own failsafe is the backup. |
| Who can stop the drone? | The safety pilot, with the radio kill switch. It doesn't depend on our code. |