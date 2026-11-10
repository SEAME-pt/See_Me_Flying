# Test data: MSP captures from the real drone

Reply frames captured on 2026-11-09 from the real drone (INAV 9.1.0), used by `test_msp.cpp` and `test_inav_decode.cpp`.

The four `.jsonl` files are unchanged copies of the ones in `telemetry/inav/captures/` (under `inav/msp/captures/`). They are copied here because only `ros2_ws` is mounted in the container, so the tests could not read the originals. The format and the state of the drone in each file are described in `telemetry/inav/captures/README.md`.

If the captures are redone, copy them here again; the tests check exact values from these files.
