---
title: Ground Station
---
# Ground station

## What is it?

The ground station is the PC that will be connected to the drone at all times, receiving, interpreting and sending information from and to the drone.

Multiple ground stations were used during the development of the project, the main three being a Raspberry Pi 5 running Raspberry Pi OS Lite with no desktop environment, a Lenovo ThinkPad P16 Gen 2 running Ubuntu 22.04 and a Lenovo Yoga 7 on Arch Linux.

The ground station has all the dependencies needed to run the project, or a way to set them up easily: on a laptop, `make up` builds the dev container (see the [root README](../README.md#quick-start)).

## How to use the Raspberry Pi

Any and all ESP12 tinkering needed for this is in the [ESP12 setup guide](../project/telemetry/README.md).

The Raspberry Pi was set up with no desktop environment since it won't be needed, and it can run most of the tools in the repo besides the simulation, for example the [MSP dashboard and gateway](../project/telemetry/msp_dashboard/README.md).

The communication from and to the drone can be done in two ways. The first one, meant for development only, is having the ESP12 connect to a network instead of creating its own. This is useful since this way we can SSH onto the Raspberry Pi and easily debug anything needed, but it adds [delay](./Telemetry_test.md). For deployment and more serious tests, use the mode where the ESP12 creates its own network and the Raspberry Pi connects to it with no interference.

When using the ESP12 connected to the SEA:ME laboratory Wi-Fi, use this command to SSH onto the Raspberry Pi:

```bash
ssh seemeflying@10.20.87.11
```

> [!WARNING]
> Keep the drone's ESP to **one client**. On Nov 18 a Raspberry Pi with a second ESP connected to the drone's ESP while a laptop ran `fc_bridge`; the link dropped out again and again and MSP RC OVERRIDE kept handing the sticks back to the radio ([motor music runs](../project/logs/measurements/motor_music/README.md)). If several tools need the drone, put [`msp_gateway`](../project/telemetry/msp_dashboard/README.md) in front as the only owner of the link.

# Tags

#hardware
