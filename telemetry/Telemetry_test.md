# Introduction

The ESP12 is the main way our [grounstation](./Groundstation) will be connected to the drone so a stable and fast connection is extremely necessary.
A wireless connection is also a good quality of life improvement since INAV allows to connect to the drone wirelessly.

# Firmware choices

More than one firmware was tested but the only ones that were really considered was [`esp-link`](https://github.com/jeelabs/esp-link) and [`micropython`](https://docs.micropython.org/en/latest/esp8266/tutorial/intro.html).

## esp-link vs micropython

Micropython is flexible, uses python3 so there's a lot of things that can be done directly onto the ESP12's firmware but there are a lot of disadvantages when compared to esp-link, namely, micropython is much heavier than esp-link and when the hardware has only 80Kb of RAM a loaded runtime like microptyhon can be a bit much.

Latency is also a very big concern, the room where the drone runs is not enormous but we receive and send a lot of information which need to come and go at the fastest rate possible, and for this, only esp-link could give us a stable and extremely fast connection.

There are two modes where both softwares were tested, first mode is where the ESP connects to the SEA:ME's network and the other one the ESP creates it's own access point and the groundstation connects directly to it. The test results bellow demonstrate the big difference between the two.

# Testing results

|        | Micropython AP | Micropython Soft | esp-link AP | esp-link Soft |
| ------ | -------------- | ---------------- | ----------- | ------------- |
| Test 1 | 92ms           | 562ms            | 10ms        | 57ms          |
| Test 2 | 96ms           | 582ms            | 12ms        | 74ms          |
| Test 3 | 84ms           | 524ms            | 9ms         | 66ms          |
| Test 4 | 96ms           | 543ms            | 15ms        | 63ms          |
| Test 5 | 89ms           | 408ms            | 13ms        | 60ms          |
This test consisted in sending and receiving MSP packages, and the ms listed is the average after sending 200 packages, the averages were taken from tests that had 0 lost packages.

# Latency measurement (STK-5.2, #82)

Measured on 2026-11-12 with `latency_test.py`, at the bench and inside the cage. Every sample is kept, including lost ones, so drops and slow replies are visible.

**Setup:** esp-link 3.2.47 in AP mode (laptop on the drone's own Wi-Fi) · INAV 9.1.0 on the OddityRC F7 AIO, MSP on UART1 at 115200 · laptop Wi-Fi power saving off · 500 requests per run, 50 ms apart, 2 s timeout.

```python3 latency_test.py --port 23 -n 500 --csv bench.csv```

| Place | Mean (ms) | Median (ms) | p95 (ms) | Max (ms) | Drops |
| --- | ---: | ---: | ---: | ---: | ---: |
| Bench | 131.1 | 40.1 | 794.4 | 1594.0 | 1.0% (5 of 500) |
| Cage | 135.7 | 100.3 | 760.0 | 1072.7 | 0.0% (0 of 500) |

No corrupted frames in either run. Raw samples: `bench.csv` and `cage.csv`.

**What it shows:**

- The link is much slower than the earlier esp-link figures above (9–15 ms). Those averages left out runs with lost packages; these include everything.
- Round-trip times fall into two groups: about half take 0–40 ms, and many of the rest take 140–180 ms. The link seems to switch between a fast and a slow mode.
- 1 reply in 20 takes over 0.75 s, and the worst took 1.6 s. Plan control loops around this tail, not the mean.
- Bench and cage are similar, so the drone's position in the room is not the main factor.

> [!TIP]  
> If power saving is enabled on the computer the results of the tests will be way higher and lost packages will be common

# TCP vs UDP

This isn't really a debate TCP is the only logical solution, esp-link does work with UDP but the micro controller would need to run esp-link client code which isn't fesable since we need inav
# Tags

#resources 