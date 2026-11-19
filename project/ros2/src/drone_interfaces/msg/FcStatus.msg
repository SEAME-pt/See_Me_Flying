# fc_bridge's view of the flight controller. Published on fc/status once a
# second and on every change.

std_msgs/Header header

string backend               # "sim" or "inav"
bool armed                   # sim: the X3 is enabled, changed with fc/arm. inav: what INAV reports
bool holding                 # fc/hold is on: setpoints are ignored and zero is sent
bool following_setpoints     # a fresh setpoint is being forwarded
float32 setpoint_age_s       # since the last accepted setpoint; -1 if none yet
bool range_valid             # the last fc/range reading was a finite distance
bool link_ok                 # inav: the FC answered in the last poll cycle. sim: always true
float32 state_age_s          # since the last reply from the FC; -1 if none yet. sim: 0
bool rc_override_active      # inav: INAV reports its MSP RC OVERRIDE mode on (the radio switch). sim: false
bool rc_sent                 # inav: fc_bridge is sending sticks (parameter rc_override). sim: false
