# ROS2 + INAV Stack — Technical Decisions

---

## ALL 1.1 — Control Rates

### Rate

The control loop will run at **50 Hz** (one cycle every **20 ms**).

- INAV's outer navigation loops don't benefit from setpoints faster than this.
- MSP over UART works as **request/response**, so every command that waits for a reply costs a full round trip. Higher rates would saturate the link without improving control.

**Minimum acceptable rate:** 20 Hz (one cycle every 50 ms).

### Timeout (Watchdog)

On the ROS2 side, the MSP bridge has a **watchdog with a 200 ms timeout** (10 missed cycles at 50 Hz, 4 at 20 Hz).

If the planner setpoint goes stale (no new data received within the timeout), the bridge stops repeating the last command and sends a **safe fallback command** (neutral hover or land) instead.

This protects the drone against ROS node crashes and frozen planners.

> **Notes:**
> - A "neutral hover" only holds position if INAV is in a position-hold mode (e.g. `NAV POSHOLD`). In `ANGLE` mode, neutral sticks keep the drone level but it will drift.
> - INAV's own **RX failsafe** is a second safety layer: if MSP RC data stops arriving entirely (e.g. the bridge or Wi-Fi dies), INAV triggers its configured failsafe procedure.

---

## ALL 1.2 — ESP8266 Transport

### Hardware

ESP module: **ESP-12F** (ESP8266-based).

### Firmware Options

| Firmware | Pros | Cons |
|---|---|---|
| **MSPWifiBridge** | MSP error checking, web configuration, Station and Access Point modes. ESP-12F is listed as supported hardware. Small, lightweight firmware. | Repository has a single commit and little community feedback, so maintenance is scarce. |
| **ESP-link** | Bidirectional bridge with built-in web management, Telnet and REST support. Good for general-purpose microcontrollers. | Transparent serial bridge: no MSP-specific packet validation. |

### Decision: MSPWifiBridge

MSPWifiBridge was chosen because it is the most suitable for INAV. It is optimized for parsing and forwarding INAV/Betaflight MSP streams efficiently over Wi-Fi.

MSPWifiBridge parses the MSP packets and relays them over TCP/UDP to our **ground station**.

### Transport Protocol: TCP

We will use **TCP** for now, because at this stage we are **configuring INAV and reading telemetry**:

- Reliability is more important than speed.
- It makes debugging easier.

> **Future change:** TCP is an initial decision. Once ROS starts actively commanding the drone, **a late command is worse than a lost one** (TCP retransmissions add latency spikes). At that point, switching to **UDP** for control traffic should be evaluated.

---

## ALL 1.3 — ROS2 Domain ID

### What it is

`ROS_DOMAIN_ID` is the number that isolates groups of ROS2 nodes running on the same physical network. ROS2 nodes automatically discover each other **only if they share the same `ROS_DOMAIN_ID`**.

### Why we need it

The SEAME network is shared between teams, so our `ROS_DOMAIN_ID` must not overlap with any other team's ID. Otherwise our nodes would see (and possibly receive commands from) other teams' nodes.

### Rules for the ID

- It must be **unique per team**.
- It must be in the range **1–101**.
  - `0` is the default, so other teams may be using it unknowingly.
  - 101 is the upper limit that is safe on all operating systems (higher values can conflict with OS ephemeral ports).

### Configuration

Set the ID in `docker-compose.yaml` for every container, so all nodes pick it up automatically:

```yaml
services:
  bridge:
    environment:
      - ROS_DOMAIN_ID=<OUR_ID>
    network_mode: host   # needed for DDS discovery across machines
```

---

## ALL 1.4 — Owners

| Area | Owners |
|---|---|
| _TBD (label unclear)_ | Miguel, Carlos, Fernando |
| Hardware | Miguel, João |
| INAV | David, Fernando, Matheus |
| ROS | João, Matheus, David |

### Sprint 1

| Member | Tasks |
|---|---|
| Miguel | STACK, HARDWARE|
| João| ROS, HARDWARE|
| Carlos | STACK  |
| David |  INAV, ROS|
| Fernando | STACK, INAV|
| Matheus| INAV, ROS|
