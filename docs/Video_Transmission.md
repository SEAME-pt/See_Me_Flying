---
title: Drone Camera on a PC
---
# Connecting to the drone's camera on a PC

> [!IMPORTANT] Requirements
> The v4l-utils package
> A 5.8 GHz receiver set to R1 (5658 MHz)
> ffmpeg

To bring the video into ROS 2 as `/image_raw` instead, see [FPV video into ROS](./FPV_Video_Receiver_Setup_UVC_Receiver_to_ROS.md).

## Install dependencies

Arch: `sudo pacman -S v4l-utils ffmpeg`
Debian: `sudo apt install v4l-utils ffmpeg`

## 5.8 GHz receiver setup

Plug the receiver into the PC and use `v4l2-ctl --list-devices`: the receiver should appear under `USB Video`. If multiple appear you can use:

```bash
ffplay -f v4l2 -fflags nobuffer -flags low_delay -framedrop /dev/videoX
```

Just replace the X at the end of this command with the number the receiver appears under.

Running this command with the correct `/dev/video` will pop up a blue picture with static; the top right of the screen shows the frequency that you'll need to match with the VTX settings in INAV.

Our drone was set up on R1, 5658 MHz. Every other band is basically the same regarding range; the only tweak to the setup was setting `vtx_power` to the lowest level possible, since that's more than enough for our use case.

> [!NOTE]
> The VTX setup in the [ELRS guide](./ELRS_Guide.md#vtx) recorded band A, channel 1 (5865 MHz). Check the current setting with `get vtx` in the INAV CLI and keep both pages in agreement.

# Tags

#guides
