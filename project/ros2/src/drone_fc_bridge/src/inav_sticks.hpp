// Velocity setpoint -> the four sticks MSP_SET_RAW_RC sends. No ROS here (the
// node copies its Twist in), so it is tested on its own.
//
// Linear for now: 1500 + 500 * v / full per axis, clamped to 1000-2000. What a
// stick then makes the drone do is up to INAV (mode, rc_expo, rates): only with
// CRUISE + POSHOLD + ALTHOLD and matching limits is it a velocity. rc_expo is
// not undone here.
//
// Signs, ROS body frame FLU -> stick (INAV source, checked on the bench
// against fc/attitude):
//   x forward +   pitch above 1500 (stick up = nose down)
//   y left +      roll below 1500  (stick right = right side down)
//   z up +        throttle above 1500
//   yaw left +    yaw below 1500   (INAV negates the yaw stick: right = nose right)

#ifndef INAV_STICKS_HPP_
#define INAV_STICKS_HPP_

#include "msp.hpp"

namespace inav
{
struct VelocitySetpoint
{
  double x{0.0};          // m/s, forward
  double y{0.0};          // m/s, left
  double z{0.0};          // m/s, up
  double yaw_rate{0.0};   // rad/s, counter-clockwise seen from above
};

// The setpoint that gives full stick on each axis. Faster is clamped to full.
struct StickConfig
{
  double full_xy{0.5};    // m/s, on x and y separately
  double full_z{0.3};     // m/s
  double full_yaw{1.0};   // rad/s
};

// Throws std::invalid_argument when a full-scale value is not a positive
// finite number. A setpoint with a NaN or inf anywhere gives centred sticks:
// one bad axis means the rest can't be trusted either.
msp::Sticks sticks_from_setpoint(const VelocitySetpoint & sp, const StickConfig & cfg = {});
}  // namespace inav

#endif  // INAV_STICKS_HPP_
