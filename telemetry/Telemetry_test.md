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

> [!TIP]  
> If power saving is enabled on the computer the results of the tests will be way higher and lost packages will be common

# TCP vs UDP

This isn't really a debate TCP is the only logical solution, esp-link does work with UDP but the micro controller would need to run esp-link client code which isn't fesable since we need inav
# Tags

#resources 