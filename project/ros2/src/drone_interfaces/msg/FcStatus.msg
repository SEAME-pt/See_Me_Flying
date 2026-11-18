# fc_bridge's view of the flight controller. Published on fc/status once a
# second and on every change.

std_msgs/Header header

string backend               # "sim" today; "inav" and "mock" later
bool armed                   # sim: the X3 is enabled. Changed with the fc/arm service
bool holding                 # fc/hold is on: setpoints are ignored and zero is sent
bool following_setpoints     # a fresh setpoint is being forwarded
float32 setpoint_age_s       # since the last accepted setpoint; -1 if none yet
bool range_valid             # the last fc/range reading was a finite distance
float32 state_age_s          # since the last FC state (sim: Gazebo odometry; inav: MSP reply); -1 if none yet
bool link_ok                 # 0 <= state_age_s <= link_timeout_s: the FC is answering
