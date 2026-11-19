// Setpoint -> sticks: zero, full scale, clamping, and each sign.

#include <gtest/gtest.h>

#include <limits>
#include <stdexcept>

#include "inav_sticks.hpp"

using inav::StickConfig;
using inav::VelocitySetpoint;
using inav::sticks_from_setpoint;

namespace
{
void expect_sticks(const msp::Sticks & s, int roll, int pitch, int yaw, int throttle)
{
  EXPECT_EQ(s.roll, roll);
  EXPECT_EQ(s.pitch, pitch);
  EXPECT_EQ(s.yaw, yaw);
  EXPECT_EQ(s.throttle, throttle);
}

VelocitySetpoint sp(double x, double y, double z, double yaw_rate)
{
  VelocitySetpoint v;
  v.x = x;
  v.y = y;
  v.z = z;
  v.yaw_rate = yaw_rate;
  return v;
}
}  // namespace

TEST(Sticks, ZeroIsCentred)
{
  expect_sticks(sticks_from_setpoint({}), 1500, 1500, 1500, 1500);
}

// One axis at a time, so a sign or a swapped axis shows up on its own.
TEST(Sticks, EachSign)
{
  const StickConfig cfg;   // 0.5 m/s, 0.3 m/s, 1 rad/s
  expect_sticks(sticks_from_setpoint(sp(0.25, 0, 0, 0), cfg), 1500, 1750, 1500, 1500);   // forward
  expect_sticks(sticks_from_setpoint(sp(-0.25, 0, 0, 0), cfg), 1500, 1250, 1500, 1500);  // back
  expect_sticks(sticks_from_setpoint(sp(0, 0.25, 0, 0), cfg), 1250, 1500, 1500, 1500);   // left
  expect_sticks(sticks_from_setpoint(sp(0, -0.25, 0, 0), cfg), 1750, 1500, 1500, 1500);  // right
  expect_sticks(sticks_from_setpoint(sp(0, 0, 0.15, 0), cfg), 1500, 1500, 1500, 1750);   // up
  expect_sticks(sticks_from_setpoint(sp(0, 0, -0.15, 0), cfg), 1500, 1500, 1500, 1250);  // down
  expect_sticks(sticks_from_setpoint(sp(0, 0, 0, 0.5), cfg), 1500, 1500, 1250, 1500);    // yaw left
  expect_sticks(sticks_from_setpoint(sp(0, 0, 0, -0.5), cfg), 1500, 1500, 1750, 1500);   // yaw right
}

TEST(Sticks, FullScaleIsFullStick)
{
  const StickConfig cfg;
  expect_sticks(sticks_from_setpoint(sp(0.5, 0.5, 0.3, 1.0), cfg), 1000, 2000, 1000, 2000);
  expect_sticks(sticks_from_setpoint(sp(-0.5, -0.5, -0.3, -1.0), cfg), 2000, 1000, 2000, 1000);
}

TEST(Sticks, FasterIsClampedToFullStick)
{
  const StickConfig cfg;
  expect_sticks(sticks_from_setpoint(sp(3, 3, 3, 30), cfg), 1000, 2000, 1000, 2000);
  expect_sticks(sticks_from_setpoint(sp(-3, -3, -3, -30), cfg), 2000, 1000, 2000, 1000);
  const double big = std::numeric_limits<double>::max();
  expect_sticks(sticks_from_setpoint(sp(big, -big, big, -big), cfg), 2000, 2000, 2000, 2000);
}

TEST(Sticks, FullScaleComesFromTheConfig)
{
  StickConfig cfg;
  cfg.full_xy = 2.0;
  cfg.full_z = 1.0;
  cfg.full_yaw = 0.5;
  expect_sticks(sticks_from_setpoint(sp(0.5, 0.5, 0.5, 0.25), cfg), 1375, 1625, 1250, 1750);
}

TEST(Sticks, RoundsToTheNearestMicrosecond)
{
  // 1500 + 500 * 0.001 / 0.5 = 1501; 0.0004 -> 1500.4 -> 1500; 0.0006 -> 1500.6 -> 1501.
  EXPECT_EQ(sticks_from_setpoint(sp(0.001, 0, 0, 0)).pitch, 1501);
  EXPECT_EQ(sticks_from_setpoint(sp(0.0004, 0, 0, 0)).pitch, 1500);
  EXPECT_EQ(sticks_from_setpoint(sp(0.0006, 0, 0, 0)).pitch, 1501);
  EXPECT_EQ(sticks_from_setpoint(sp(-0.0006, 0, 0, 0)).pitch, 1499);
}

// The result always goes to build_set_raw_rc, which throws outside 1000-2000.
TEST(Sticks, AlwaysInsideWhatTheBuilderTakes)
{
  for (double v = -5.0; v <= 5.0; v += 0.01) {
    const auto s = sticks_from_setpoint(sp(v, -v, v, -v));
    EXPECT_NO_THROW(msp::build_set_raw_rc(s)) << "v=" << v;
  }
}

TEST(Sticks, NonFiniteSetpointIsCentred)
{
  const double nan = std::numeric_limits<double>::quiet_NaN();
  const double inf = std::numeric_limits<double>::infinity();
  expect_sticks(sticks_from_setpoint(sp(nan, 0.5, 0, 0)), 1500, 1500, 1500, 1500);
  expect_sticks(sticks_from_setpoint(sp(0.5, inf, 0, 0)), 1500, 1500, 1500, 1500);
  expect_sticks(sticks_from_setpoint(sp(0.5, 0, -inf, 0)), 1500, 1500, 1500, 1500);
  expect_sticks(sticks_from_setpoint(sp(0.5, 0, 0, nan)), 1500, 1500, 1500, 1500);
}

TEST(Sticks, RefusesABadConfig)
{
  const double bad[] = {0.0, -0.5, std::numeric_limits<double>::quiet_NaN(),
    std::numeric_limits<double>::infinity()};
  for (double b : bad) {
    StickConfig xy, z, yaw;
    xy.full_xy = b;
    z.full_z = b;
    yaw.full_yaw = b;
    EXPECT_THROW(sticks_from_setpoint({}, xy), std::invalid_argument) << b;
    EXPECT_THROW(sticks_from_setpoint({}, z), std::invalid_argument) << b;
    EXPECT_THROW(sticks_from_setpoint({}, yaw), std::invalid_argument) << b;
  }
}
