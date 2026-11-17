# Introduction

Our team's final goal is to create software that will autonomously fly a non-autonomous drone. The limitations of using a drone that wasn't designed for this are clear, and we are very aware of them.
With that in mind, some modifications had to be made, namely the installation of an ESP12 module and a PMW3901 module that were already provided to us. However, we quickly realized that the ThoneFlow PMW3901 module has some limitations that we believe will hold us back in the future.

# INAV

INAV (Intelligent Navigation system for Aerial Vehicles) is open-source flight controller software that focuses heavily on GPS-based navigation and autonomous capabilities for various types of RC vehicles.
Our group opted to use it instead of Betaflight because of its autonomous capabilities, believing it will allow us to go further and reach a more satisfactory final result.

# The limitations found

The ThoneFlow we have is one of the most bare-bones implementations of the [PMW3901 sensor](https://px4.gitbook.io/px4-user-guide/drone_parts/peripherals/optical_flow/pmw3901#hex-hereflow-pmw3901-optical-flow-sensor). It is only an optical flow sensor, and it communicates with INAV through an old, rarely maintained third-party protocol called CXOF. The optical flow sensor can measure how fast the image moves, but without a rangefinder it can't convert that into the drone's actual velocity. For that, it would need an external rangefinder.

## A solution

Every issue we found with our ThoneFlow made us wonder whether there were other options on the market. That's a silly question; of course there are plenty of optical flow boards for sale. However, we also need to be cost-efficient and think about weight.

### CubePilot's HereFlow

The list of boards that use the PMW3901 is not very extensive, and CubePilot's HereFlow is by far the best equipped, coming with a gyroscope, a rangefinder and optical flow. However, there are two big catches. First, it is DroneCAN only, so it doesn't communicate with the flight controller through UART, which is the only option we have. From the get-go, this option was discarded. The second big catch is the price: 175€ is something we can't justify at all.

### MicoAir MTF-02P

The MTF-02P doesn't use a PMW3901; it uses a PAW3902 sensor, which has much better low-light performance than the PMW3901. Alongside the rangefinder and the improved low-light performance, this option from MicoAir has an excellent INAV implementation and already communicates through the MSP protocol, which INAV uses and which our whole project already revolves around.
It is also very cost-efficient: it's a bit more expensive than the ThoneFlow but packs a much bigger punch.

# Verdict

|                         | ThoneFlow-3901U                      | MicoAir MTF-02P                                       | CubePilot HereFlow            |
| ----------------------- | ------------------------------------ | ----------------------------------------------------- | ----------------------------- |
| Flow chip               | PMW3901                              | PAW3902                                               | PMW3901                       |
| Chip release (approx.)  | ~2016–2017                           | ~2018–2019                                            | ~2016–2017                    |
| Low-light performance   | Fair                                 | Good                                                  | Fair                          |
| Rangefinder             | No                                   | Yes, built-in ToF                                     | Yes, built-in ToF             |
| Interface               | UART                                 | UART                                                  | DroneCAN only                 |
| Protocol                | CXOF (legacy third-party)            | MSP (also MAVLink)                                    | DroneCAN                      |
| INAV support            | Yes, legacy driver                   | Yes, native MSP path                                  | No                            |
| Ports needed on our FC  | 1 UART                               | 1 UART                                                | CAN port                      |
| Extra hardware needed   | Separate rangefinder                 | None                                                  | CAN-capable flight controller |
| Price                   | ~15€                                 | ~22€                                                  | ~175€                         |
| Verdict for our project | Usable, but limited                  | Best fit                                              | Discarded                     |
# Examples we've found

[micoair tutorial and demo](https://www.youtube.com/watch?v=bEKm-PGRnks)