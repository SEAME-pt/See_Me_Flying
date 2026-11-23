# `inav` backend on the real drone, Nov 16

`fc_bridge backend:=inav` on the ground laptop, joined to the drone's Wi-Fi (esp-link, `192.168.4.1:23`). Props off, not armed, no rangefinder fitted, Configurator closed.

## Rates

From the bag (43.3 s), the same as `ros2 topic hz` live:

| Topic | Messages | Rate |
| --- | --- | --- |
| `fc/attitude`, `fc/odom` | 431 | 10.0 Hz |
| `fc/optical_flow` | 430 | 9.9 Hz |
| `fc/battery` | 86 | 2.0 Hz (every 5th cycle) |
| `fc/status` | 43 | 1.0 Hz (timer) |
| `fc/range` | 0 | no rangefinder, as expected |

All five messages of a cycle are requested at once, so this is the full 10 cycles/s. Nov 9's sequential polling of nine messages managed 0.9–3.2 cycles/s.

## Signs

| Move | `fc/attitude` | ROS expects |
| --- | --- | --- |
| Turn left (counter-clockwise from above) | yaw increases | yaw increases |
| Nose down | pitch increases | pitch increases |
| Right side down | roll increases | roll increases |

All match: the conversion needs no fix.

## Link loss

- **Short gaps:** now and then (about once every 1–2 minutes) one cycle gets no reply; the next ones do, within 150–500 ms, without a reconnect.
- **Battery pulled for a few seconds** (the ESP is soldered on, so this restarts it and the FC together): the silent link was caught after 4 cycles (0.75 s) and the backend reconnected. esp-link came back before INAV answered, so the startup check refused that connection and tried again. Link up 4.5 s after it was lost, with nothing touched.
- One reconnect earlier in the session; not noted whether it happened by itself.

## The bag

`bag/` (MCAP, 474 KB), the six `fc/*` topics while the drone was tilted and turned by hand. It plays back with `fc_bridge` stopped, inside the container (`make shell`):

```bash
ros2 bag play ~/project/logs/measurements/inav_link/2026-11-16_dbf5804/bag
```

Not checked: battery voltage against a multimeter.
