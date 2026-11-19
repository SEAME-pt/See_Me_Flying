---
title: Wi-Fi Latency Tests
---
# Wi-Fi latency tests

The ESP12 is the main way our [ground station](./Groundstation.md) is connected to the drone, so a stable and fast connection is essential.
A wireless connection is also a good quality of life improvement, since INAV allows connecting to the drone wirelessly.

## Firmware choices

More than one firmware was tested, but the only ones really considered were [`esp-link`](https://github.com/jeelabs/esp-link) and [`micropython`](https://docs.micropython.org/en/latest/esp8266/tutorial/intro.html). The drone runs esp-link; setup in the [ESP12 setup guide](../project/telemetry/README.md).

### esp-link vs MicroPython

MicroPython is flexible and uses Python 3, so a lot can be done directly in the ESP12's firmware, but it has disadvantages compared to esp-link: MicroPython is much heavier, and when the hardware has only 80 KB of RAM a runtime like MicroPython can be a bit much.

Latency is also a very big concern. The room where the drone flies is not enormous, but we receive and send a lot of information that needs to come and go as fast as possible, and only esp-link gave us a stable and fast connection.

Both firmwares were tested in two modes: **station**, where the ESP joins the SEA:ME network, and **AP**, where the ESP creates its own access point and the ground station connects directly to it. The results below show the big difference between the two.

## Testing results

|        | MicroPython AP | MicroPython station | esp-link AP | esp-link station |
| ------ | -------------- | ------------------- | ----------- | ---------------- |
| Test 1 | 92 ms          | 562 ms              | 10 ms       | 57 ms            |
| Test 2 | 96 ms          | 582 ms              | 12 ms       | 74 ms            |
| Test 3 | 84 ms          | 524 ms              | 9 ms        | 66 ms            |
| Test 4 | 96 ms          | 543 ms              | 15 ms       | 63 ms            |
| Test 5 | 89 ms          | 408 ms              | 13 ms       | 60 ms            |

This test consisted of sending and receiving MSP packets; each value is the average over 200 packets, taken from runs that had 0 lost packets.

## Latency measurement (STK-5.2, #82)

Measured on 2026-11-12 with `project/telemetry/latency_test.py`, at the bench and inside the cage. Every sample is kept, including lost ones, so drops and slow replies are visible.

**Setup:** esp-link 3.2.47 in AP mode (laptop on the drone's own Wi-Fi) · INAV 9.1.0 on the OddityRC F7 AIO, MSP on UART1 at 115200 · laptop Wi-Fi power saving off · 500 requests per run, 50 ms apart, 2 s timeout.

```bash
python3 project/telemetry/latency_test.py --port 23 -n 500 --csv bench.csv
```

| Place | Mean (ms) | Median (ms) | p95 (ms) | Max (ms) | Drops |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bench | 131.1 | 40.1 | 794.4 | 1594.0 | 1.0% (5 of 500) |
| Cage | 135.7 | 100.3 | 760.0 | 1072.7 | 0.0% (0 of 500) |

No corrupted frames in either run. The raw samples (`bench.csv` and `cage.csv`) weren't committed.

**What it shows:**

- The link is much slower than the earlier esp-link figures above (9–15 ms). Those averages left out runs with lost packets; these include everything.
- Round-trip times fall into two groups: about half take 0–40 ms, and many of the rest take 140–180 ms. The link seems to switch between a fast and a slow mode.
- 1 reply in 20 takes over 0.75 s, and the worst took 1.6 s. Plan control loops around this tail, not the mean.
- Bench and cage are similar, so the drone's position in the room is not the main factor.

> [!TIP]
> If power saving is enabled on the computer, the results will be much higher and lost packets will be common.

### Measuring it again

`make wifi-rtt` runs the same script and keeps the result in `project/logs/measurements/wifi_rtt/` (a dated folder plus a line in `history.csv`). Pass the port, since the script still defaults to 5760, the old MicroPython bridge's port:

```bash
make wifi-rtt NOTE="cage, AP mode, radio on" ARGS="--port 23 -n 500"
```

How the logbook works: [Logs](../project/logs/README.md).

## TCP vs UDP

This isn't really a debate: TCP is the only workable choice. esp-link does support UDP, but the other end would need to run esp-link's client code, which isn't feasible since the flight controller runs INAV.

# Tags

#tests
