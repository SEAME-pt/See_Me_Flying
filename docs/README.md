
The hardware given to us is very straightforward, a Pilotix Brook 2.5" fully equiped and ready to fly. Some supporting tools were also given to us, a RadioMaster Pocket controller and some modules, namely, a PMW 3901 sensor and an ESP12-E WiFi module.

## The Drone

The Pilotix Brook 2.5" is actually the name of the kit, the frame and the propeller guards, everything else is customizable so we had to discover what our drone came equipped with.

After a lot of research this is a list of parts and what they do.

### OddityRC F7 40

This is the flight controller, every drone needs one, it's like the motherboard of the computer, everything is solder on to it, it has a total of 5 [[UART interfaces]], 2 of them came already filled, one for the video system and the other for the ELRS receiver.

This specific board came flashed with Betaflight, a great program for FPV not so much for an autonomous drone so we took the liberty to flash it with another compatible software called [[INAV]] which can communicate with the [[UART interfaces]] and also be used of autonomous flying

### Video transmission system

#### Caddx Ratel 2

A small analog camera with surprisingly good video quality perfect for FPV usage, in our case, it will be used as a big source of information and used to guide the drone and tell him where he can go.

#### Ratel 2.0 Cherry Angle MMCX RHCP Antenna

A video transmission antenna that, in normal FPV use, exists so the pilot can see through the camera using a pair of FPV goggles.

#### PandaRC VT5804 Bat Lite 1300mw 5.8Ghz VTX

A powerfull video transmitter with more than enough range for our use case

### ELRS Receiver

The ELRS Reicever that came soldered into our drone is quite the mystery, in most listing for this drone it says "ELRS 2.4GHz" which is true, we know this because we can connect to the drone through ELRS using the RadioMaster Pocket. We couldn't figure out any brand or 

---

> [!NOTE]  
> Motors used and propellers aren't that important in this project since no great aditional load was added to the drone so we didn't worried about testing on how much weight the drone could handle or fly around with.

---
## Additional hardware

### PMW 3901 Sensor

An optical flow sensor that enhances the drone stability without using gps capabilities.

It communicates to the board through UART interface and it has no distance sensor onboard unlike other 3901 sensors

This sensor has a very small notch on the "camera", that notch points to the back of the drone

Our model is specifically the Thone ThoneFlow-3901U which is basically the same sensor as the Holybro PMW3901 but it doesn't come presoldered it does not come inside a 3D printed case.

### ESP12-E WiFi

A compact and low-power device created for IoT applications. It comes with an ESP8266 and an onboard antenna.

It connects to the flight controller through the UARTs and it can use [[MSP]] to communicate with a ground computer.

We flashed ours with MicroPython.

---

## Mounts

The drone has no mounts for the ESP and PMW so we took the liberty to model some mounts using blender

> [!NOTE]  
> None of the members had previous experience with 3D modelling and 3D printing so there was a lot of trial and error

The SEA:ME 3D printer is a **[[Wanhao Duplicator 12-230]]** which has a ready to go Cura profile but the team opted in using the PrusaSlicer since there was no easy way to install the Wanhao version on Linux, so tinkering on the profile was necessary for each print.

The mount for the PMW module is meant to go on the underside of the drone and screwed with the screws that already come installed on the bottom plate of the drone.

The mount for the ESP12 was tricky since the module is so much bigger than the PMW, these mounts were made to replace the GoPro that came equipped with the drone.

## Hardware limitations

The drone and modules offered to us are very capable but they all have very clear limitations that we had to deal with during the project.

### PMW 3901

The ThoneFlow-3901U is the most barebones a 3901 module can get, it has no external distance sensor and it comes with no bells and whistles and from the two models that expose the module through an UART interface it's the one that doesn't come with pre-soldered wires.

None of these would be a problem for people that already know how to solder and are accustomed with dealing with such small parts, something that none of us were.

The biggest hurdle is not having an external distance sensor that would be a really big help.

### Pilotix Brook 2.5"

The drone that was offered to us is an amazing FPV drone kitted out with amazing high RPM motors, carbon fibre frame and a TBS crossfire antenna and a modified version of the OddityRC F7 flashed with BetaFlight.

The TBS Crossfire antenna had to be removed and changed out for an ExpressLRS antenna because having a proprietery antenna was a no go for our project.

BetaFlight is the industry standard when it comes to FPV firmware, but it has absolute no autonomous flight capabilities and it's communications to the UART interfaces isn't ideal so we changed it for [[INAV]]

Battery life was also a constraint that comes with the drone specifications, the high KV motors that the drone uses are amazing for speed and nimble drones but, at full throtle, use up way more battery than a lower KV motor and we don't plan to run the drone on super high speeds so the higher KV count is completely wasted.

## Wiring

![[wire_diagram.png]]

[[Sources]]