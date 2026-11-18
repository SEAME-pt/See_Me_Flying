# fc_bridge, backend inav: the RC channels INAV is using (MSP_RC), after the
# MSP RC override, so they show ROS's sticks while the override is on and the
# radio's otherwise. In µs: 1000-2000 at full stick, 1500 centred. Not
# published by the sim backend.

std_msgs/Header header

uint16 roll        # above 1500: right side down
uint16 pitch       # above 1500: nose down (forward)
uint16 yaw         # above 1500: nose right
uint16 throttle
uint16[] channels  # all of them, in INAV's order: roll, pitch, yaw, throttle, AUX1, ...
