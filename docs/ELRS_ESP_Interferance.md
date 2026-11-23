---
title: ELRS and ESP Interference Test
---
# ELRS and ESP interference test

Both the ELRS receiver and the ESP12 talk on the same frequency, 2.4 GHz. This raised the question of whether the two could interfere, and if they do, how we could test it and correct it.

Our drone is being made with only the SEA:ME laboratory in mind, so we assumed from the start that the two would coexist with no major problems, but the tests were run to give us peace of mind.

The tests were run using the telemetry and log function of EdgeTX on our RadioMaster Pocket, noting the values explained below:

| Value | Meaning |
| ---- | -------------------------------------------------------------------------------- |
| 1RSS | Signal strength in dBm, close to 0 is good |
| RQly | Receiver link quality; if this hits 0 the failsafe triggers |
| RSNR | Signal-to-noise ratio in dB; this is what shows the noise from any interference |
| TQly | Quality of the packets that come from the drone |
| TRSS | Signal strength of the drone's telemetry |
| TSNR | Signal-to-noise ratio on the controller |

## Results

Every value barely changes between the tests, so there's no worry about the two of them colliding. Every value looks good and shows nothing to worry about.

| Value | ESP off | ESP under stress |
| ----- | ------- | ---------------- |
| 1RSS  | -44 dBm | -41 dBm          |
| RQly  | 97%     | 99%              |
| RSNR  | 12 dB   | 11 dB            |
| TQly  | 98%     | 98%              |
| TRSS  | -37 dBm | -41 dBm          |
| TSNR  | 12 dB   | 15 dB            |

The radio setup itself is in the [ELRS guide](./ELRS_Guide.md); the ESP12 in the [ESP12 setup guide](../project/telemetry/README.md).

# Tags

#tests
