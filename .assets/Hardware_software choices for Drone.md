The drone now runs **INAV 9.1.1** on a custom **`ODDITYRCF7AIO`** target, with its board alignment and accelerometer calibration verified on the bench.

**Reasoning of choices of Embedded Operating System:**

**Ardupilot** can’t run on the drone. The drone board’s chip, the STM32F722RET6, has 512 KB of internal flash. This is insufficient for running Ardupilot’s most trimmed-down builds for small boards, which require at least 1 MB.

**Betaflight** was a possible choice, but one that we eventually decided against. Ultimately, it has a different focus, best on manually piloted drones. It lacks support for the ThoneFlow-3901U optical flow sensor, and for Optical flow position hold, mandating that all of the information regarding it be fully handled off-drone.

**Inav** bears greater similarities to the usage of PSX4, that we’ll use for flight simulation, diminishing the sim-to-reality gap compared to Betaflight.  
It boasts onboard barometer altitude hold, controlled emergency landing on radio loss, and optical flow support, which natively requires a rangefinder, but software workarounds exist. The support for the specific ThoneFlow protocol requires a test, and might require using the WiFi module to translate the data.

No target existed for our specific build, so we took a very similar F7 from Aocorda, **AOCODARCF722AIO**, and changed its info regarding **gyro alignment** (`CW180_DEG` → `CW90_DEG`, a yaw correction of \-90°), **led pins** (LEDs PA4 → PA14 (LED0) & PA13 (LED1)), and the sensor scale (250 → 179\)

**Software setup steps and challenges:**

**Betaflight backup** on ver 4.5.1 (build key a72a9e7809ef36ab0db31291e4b21362). Its diff all and CLI outputs (version, status, serial, resource, aux, get vbat, get failsafe, get pinio, get msp\_override) were saved as a fallback.

Update of **Radio Controller Firmware** to Queen Anne’s Revenge (09/02/2026), and **ExpressLRS** to version 4.0.

**Killswitch setup** on ARM on channel 5 (AUX1), and PREARM on channel 6 (AUX2), active in a high range for these two state switches, expected to hit 2000 (1700-2100 \= armed), with a prearm timeout of 1 second (INAV default is 10\)

Recorded **Electronic Speed Controller** (Bluejay) settings, which required battery power, to guarantee the right orientation for motor spin in the INAV configuration.

**Betaflight's board alignment** and the physical mounting did not agree with INAV measurements. This was fixed with the Sensors tab readings after some trial and error. 

For **INAV axis calibration,** it accepts positions up to about 33° off, so "recognized" does not mean correct. The values were originally very off, so we continuously recalibrated until all three acc gain values (for accelerometer’s gravity measurements) sat near 4096 (X 4096 Y 4098 Z 4095\)

The original **custom INAV target** had a bug regarding the gyro, present only in the 9.1.0 version of the Aocoda base target. This was found by comparing branches, as it was not on the 10.0.0 version.

**Settings found in the diff that mattered for INAV:**

| Betaflight setting | Value | Meaning |
| :---- | :---- | :---- |
| align\_board\_yaw | 135 | Board rotation in the frame; turned out not to describe this drone correctly in INAV |
| motor\_output\_reordering | 2,3,0,1 | Motor 1 on PB0, 2 on PB1, 3 on PB4, 4 on PB5 (checked in Betaflight source) |
| yaw\_motors\_reversed | ON | Props-out |
| motor\_pwm\_protocol | DSHOT300 | ESC protocol |
| motor\_poles | 12 | For RPM data |
| vtx\_power | 5 | 1.3 W, far too high for the cage |
| ARM on AUX1 (ch5), PREARM and ANGLE on AUX2 | (modes) | Two-switch arming interlock |
| failsafe\_procedure | DROP, 1.5 s guard | Disarm on radio loss |
| msp\_override\_failsafe | OFF | Wi-Fi path cannot keep the drone flying on radio loss |
| vbat\_warning\_cell\_voltage / vbat\_min\_cell\_voltage | 3.50 V / 3.30 V | With 100% sag compensation |

