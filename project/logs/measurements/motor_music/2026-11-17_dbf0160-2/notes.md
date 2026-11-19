# The motors play the melody through ROS, Nov 17

`scripts/motor_music/sing.sh play` (commit dbf0160), the first pass of an RTTTL ringtone (12.3 s, 18 notes, G5–G6). Props off, armed from the radio, SA on. FC on **control profile 2 with roll, pitch and yaw PIDs at zero**, so the motors get the throttle alone. Relative tuning, `--base 1150`, zero point 976 (the old default). Heard: **recognizable**.

`song.wav` is silent: the laptop's mic records no real sound (a 1 kHz beep from its own speaker doesn't show up), so there is no recording of the performance in this folder.

## What the bag shows

- **The four motors were identical on every note** (`fc/motors`, spread 0): with zero PIDs nothing but the throttle reaches them. In the earlier calibration on the normal profile, the stabilisation wound up within a second and held the motors at about [1720, 1400, 1400, 1080] whatever the throttle (`../2026-11-17_ab84ee9-4/`).
- **INAV gives the motors stick − 20:** motor = 1.0219 × stick − 45.1 over 1150–1324, within 1 µs. So DShot 0 (motor 1058, `throttle_idle` 8 %) is at stick ≈ 1079, not the 976 the tuning assumed. The intervals came out too wide: the octave G5–G6 was ×3.4 in DShot instead of ×2, the low notes stretched the most. Tried zero 1079 and base 1250 after this run: by ear it sounded worse, so the defaults went back to 976 and 1150 (the motors probably don't speed up in proportion, and the wider intervals make up for it).
- **Timing:** each note's stick reached INAV 150–270 ms after it was published (the bridge tick, the poll cycle and Wi-Fi), so the whole melody runs about 0.2 s late with about ±60 ms jitter per note. The 0.27 s notes are the ones that suffer.

## Still assumed

Motor speed proportional to the DShot command (unloaded, so roughly; friction makes the lowest speeds slower than proportional). Only the ear checks it, until a mic hears the motors.
