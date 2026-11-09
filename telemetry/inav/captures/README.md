# MSP captures (INAV-4.2, #125)

Raw MSPv2 replies from the drone, for testing the ROS-6.2 decoders. They were captured with `msp_inventory.py capture` on 2026-11-09.

**Setup:** OddityRC F7 AIO (ODF7) on INAV 9.1.0 · esp-link 3.2.47 on UART1 · laptop on the drone's own Wi-Fi · props off · battery connected · receiver not bound (no RC link).

## File format

Each file is JSON Lines. The first line records the setup and the state. Every other line is one request:

```json
{"name": "MSP_ATTITUDE", "cmd": 108, "i": 0, "ok": true, "rtt_ms": 26.1, "hex": "24583e006c0006…"}
```

- `hex` is the full reply frame: `$X>`, flag, command (2 bytes), size (2 bytes), payload, CRC. The payload starts at byte 8.
- `ok: false` means the reply arrived with a bad CRC or as an error frame. Use these lines to test that the decoder rejects them.
- Lines with `"error": "timeout"` got no reply. They have no `hex`.

Payload layouts and units are in `inav/msp/candidates.md`.

## States

Roll, pitch and yaw are from MSP_ATTITUDE in the capture. Fill in the Configurator column from your notes; the decoder output should match it to within a degree.

| File | How the drone was set up | Configurator values | What the capture shows |
| --- | --- | --- | --- |
| `flat_still.jsonl` | Level on two books, still, radio switched on | roll …, pitch …, heading …, … V, modes … | roll −0.4 to −1.1°, pitch −5.9 to −6.4°, yaw 48–49° · acc Z ≈ +507 · battery 16.2 V · the FC did not see the radio: RC link blocker and FAILSAFE still active, RC channels at placeholder values |
| `radio_off.jsonl` | Level on two books, still, radio off | roll …, pitch …, heading …, … V, modes … | roll −3.5 to −4.0°, pitch −6.5°, yaw 1° · acc Z ≈ +493 (right side up) · battery 16.3 V · active mode FAILSAFE · arming blocked by: sensors calibrating, RC link, prearm |
| `tilted.jsonl` | One side raised, held still | roll …, pitch … | roll 45.2 to 46.6°, pitch −10.7 to −12.0° · acc Y 366, Z 354 (consistent with ~46° roll) · arming also blocked by "not level" |
| `flow_moving.jsonl` | Slid by hand over a patterned surface during the run | direction moved: … | flow rate X up to 56 °/s, Y up to 9 °/s · flow quality 100, dropping to 0 for a moment · gyro up to ±19 °/s from hand wobble |

## Not captured yet

`radio_on` needs the receiver bound to the radio; RC channels currently read fixed placeholder values. Capture it once the receiver is bound, and capture `flat_still` again at the same time, since this one has no RC link.

## Notes for decoder tests

- **Mode bitmask:** the active mode is bit 17, which is `FAILSAFE`, the 18th name in this drone's MSP_BOXNAMES reply.
- **Rangefinder:** MSP_SONAR_ALTITUDE reads 0 cm, but the rangefinder bit is not set in the MSP2_INAV_STATUS sensor bitmask (`0xa3`: acc, baro, optical flow, temperature). No sensor is fitted, so 0 cm must be treated as invalid.
- **Local pose:** position and velocity read 0 throughout, because INAV has no position estimate while disarmed on the bench. Attitude in the same message matches MSP_ATTITUDE.
- **Altitude:** the estimate reads 0; the baro altitude moves between −85 and +41 cm from sensor noise.
- **Lost replies:** about 19–24% of requests timed out in each file. MSP_BOXNAMES (the longest reply, 368 bytes as a frame) got through only 1 to 8 times out of 20. Every message still has at least one good reply in every file.
- **Damaged frames:** `flat_still.jsonl` has three MSP_BOXNAMES replies marked `ok: false`. Bytes are missing from the middle of the reply and the next reply's start follows straight after, so the CRC fails. Use them to test that the decoder rejects damaged frames.

## Medians of the three runs

| Message | Rate alone (Hz) | Median RTT (ms) | p95 RTT (ms) | Loss (%) |
| --- | ---: | ---: | ---: | ---: |
| MSP2_INAV_STATUS | 10.4 | 15.8 | 827 | 0.0 |
| MSP_ATTITUDE | 12.1 | 13.9 | 631 | 0.6 |
| MSP_ALTITUDE | 11.4 | 14.0 | 777 | 0.6 |
| MSP_RAW_IMU | 11.1 | 14.0 | 466 | 0.9 |
| MSP2_INAV_ANALOG | 4.8 | 18.2 | 971 | 2.0 |
| MSP2_INAV_OPTICAL_FLOW | 11.9 | 13.8 | 784 | 0.0 |
| MSP_RC | 5.0 | 17.5 | 906 | 2.0 |
| MSP_SONAR_ALTITUDE | 13.7 | 12.5 | 229 | 0.7 |
| MSP2_INAV_FULL_LOCAL_POSE | 9.1 | 17.9 | 439 | 2.2 |
| MSP_NAV_STATUS | 12.6 | 13.9 | 739 | 0.0 |
| MSP2_INAV_GET_LINK_STATS | 8.8 | 16.4 | 551 | 3.3 |
| MSP_MOTOR | 14.3 | 14.1 | 205 | 0.7 |

**Full set** (the 9 live messages polled in turn): 1.4 cycles/s (runs: 1.4, 1.6, 1.2).

**Conditions:** 2026-11-09 · INAV 9.1.0 on ODF7 · esp-link 3.2.47, UART1 at 115200 baud · laptop on the drone's own Wi-Fi · sequential polling, no gap · 1500 ms reply timeout · 10 s per message · raw output in `run1.txt` to `run3.txt`.