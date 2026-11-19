# fc_bridge, backend inav: what INAV sends each motor (MSP_MOTOR), in µs.
# Stopped (disarmed) reads about 1000 on our drone. In the mixer's motor
# order; on a quad X with the default mixer: 1 rear right, 2 front right,
# 3 rear left, 4 front left.
# Not published by the sim backend.

std_msgs/Header header

uint16[] motors   # one per motor the mixer drives
