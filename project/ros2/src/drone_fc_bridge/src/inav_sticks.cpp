#include "inav_sticks.hpp"

#include <algorithm>
#include <cmath>
#include <stdexcept>

namespace inav
{
namespace
{
constexpr double CENTRE_US = 1500.0;
constexpr double HALF_RANGE_US = 500.0;

// sign = +1: positive v pushes the stick up; -1: down.
uint16_t stick(double v, double full, int sign)
{
  const double frac = std::clamp(sign * v / full, -1.0, 1.0);
  return static_cast<uint16_t>(std::lround(CENTRE_US + HALF_RANGE_US * frac));
}

bool positive_finite(double v)
{
  return std::isfinite(v) && v > 0.0;
}
}  // namespace

msp::Sticks sticks_from_setpoint(const VelocitySetpoint & sp, const StickConfig & cfg)
{
  if (!positive_finite(cfg.full_xy) || !positive_finite(cfg.full_z) ||
    !positive_finite(cfg.full_yaw))
  {
    throw std::invalid_argument("stick full-scale values must be positive and finite");
  }
  msp::Sticks s;   // centred
  if (!std::isfinite(sp.x) || !std::isfinite(sp.y) || !std::isfinite(sp.z) ||
    !std::isfinite(sp.yaw_rate))
  {
    return s;
  }
  s.pitch = stick(sp.x, cfg.full_xy, +1);
  s.roll = stick(sp.y, cfg.full_xy, -1);
  s.throttle = stick(sp.z, cfg.full_z, +1);
  s.yaw = stick(sp.yaw_rate, cfg.full_yaw, -1);
  return s;
}
}  // namespace inav
