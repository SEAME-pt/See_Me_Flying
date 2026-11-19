
# What is it?

The ground station is the PC that will be connected to the drone at all times, receiving, interpreting and sending information from and to the drone.

Multiple ground stations were used during the development of the project being the main three a Raspberry PI 5 running Raspberry OS Lite with no desktop environment, a Lenovo ThinkPad P16 Gen 2 running Ubuntu 22.04 and a Lenovo Yoga 7 on Arch Linux.

The ground station has all the dependencies needed to run the project or have a way to easily setup it.

# How to use the Raspberry PI

Any and all ESP12 tinkering needed for this is present on the [guide](./README.md).

The raspberry was setup with no desktop environment since it won't be needed and it can run most of the tools provided in the repo besides the simulation.

The communication from and to the drone can be done in two ways. The first one that is meant for development only is having the ESP12 connect to a network instead of creating it's own, this one is useful since this way we can ssh onto the raspberry PI and easily debug anything needed, this of course has added [delay](./Telemetry_test.md). For deployement and more serious tests the mode where the ESP12 creates it's own network and the raspberry pi can connect to it with no interferance should be used.

When using the ESP12 connected to the SEAME's laboratory WiFi use this command to SSH onto the raspberry PI:

```bash
ssh seemeflying@10.20.87.11
```


# Tags

#hardware 