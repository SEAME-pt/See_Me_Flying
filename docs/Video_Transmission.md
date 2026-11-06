# Connecting to the drone's camera on a PC


> [!IMPORTANT] Requirements  
> The v4l utils package
> A 5.8GHz receiver set to R1 (5681MHz)
> ffmpeg


## Install dependencies

Arch: `sudo pacman -S v4l-utils ffmpeg`
Debian: `sudo apt install v4l-utils ffmpeg`

## 5.8GHz receiver setup

Plug the receiver to the PC and use `v4l2-ctl --list-devices` the receiver should appear under `USB Video` if multiple appear you can use:
```bash
ffplay -f v4l2 -fflags nobuffer -flags low_delay -framedrop /dev/videoX
```
Just replace the X at the end of this command so it represents the one that the receiver appears under.

Running this command with the correct `/dev/video` will popup a blue picture with static, the top right of the screen shows the frequency that you'll need to match with the VTX settings of INAV

Our drone was setup with the R1 5658MHz, every other band is basically the same regarding range, the only tweak to the setup was setting the vtx_power at the lowest level possible since that's more than enough for our use case.

# Tags

#guides 
