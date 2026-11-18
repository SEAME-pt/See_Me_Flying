# Optical flow as INAV reports it (MSP2_INAV_OPTICAL_FLOW), in ROS units.
# Published on fc/optical_flow by fc_bridge. The sim's flow model fills
# the same fields, so code above fc_bridge can't tell sim from real.

# INAV sends the rates as signed whole degrees per second; fc_bridge
# converts them to rad/s.

# Axes: ROS body frame (x forward, y left, z up), right-hand rule.
# flow_rate is written like a gyro rate: rotating in place over the floor
# gives flow_rate == body_rate, so (flow_rate - body_rate) is the part
# caused by moving. At height h above a flat floor, roughly:
#   forward speed v_x = -(flow_rate_y - body_rate_y) * h
#   left speed    v_y =  (flow_rate_x - body_rate_x) * h
# To confirm on the real sensor: tilt in place over texture; flow and
# body rates should cancel (roadmap Phase 7).

std_msgs/Header header

uint8 quality          # 0-255 as INAV reports it; 0 = no usable flow
float32 flow_rate_x    # rad/s about body x, convention above
float32 flow_rate_y    # rad/s about body y
float32 body_rate_x    # rad/s, gyro over the same interval, body x
float32 body_rate_y    # rad/s, body y
