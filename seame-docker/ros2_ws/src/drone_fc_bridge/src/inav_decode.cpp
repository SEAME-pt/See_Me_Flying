#include "inav_decode.hpp"

#include <cstddef>

namespace inav
{
namespace
{
constexpr double PI = 3.14159265358979323846;
constexpr double DEG = PI / 180.0;   // rad per degree

// Little-endian reads. INAV writes most signed values through its unsigned
// write calls, so the signed readers just reinterpret the same bytes.
uint16_t u16(const Payload & p, std::size_t at)
{
  return static_cast<uint16_t>(p[at] | (p[at + 1] << 8));
}

int16_t i16(const Payload & p, std::size_t at)
{
  return static_cast<int16_t>(u16(p, at));
}

uint32_t u32(const Payload & p, std::size_t at)
{
  return static_cast<uint32_t>(p[at]) | (static_cast<uint32_t>(p[at + 1]) << 8) |
         (static_cast<uint32_t>(p[at + 2]) << 16) | (static_cast<uint32_t>(p[at + 3]) << 24);
}

int32_t i32(const Payload & p, std::size_t at)
{
  return static_cast<int32_t>(u32(p, at));
}
}  // namespace

std::optional<ApiVersion> decode_api_version(const Payload & p)
{
  if (p.size() < 3) {
    return std::nullopt;
  }
  ApiVersion v;
  v.protocol = p[0];
  v.api_major = p[1];
  v.api_minor = p[2];
  return v;
}

std::optional<FcVariant> decode_fc_variant(const Payload & p)
{
  if (p.size() < 4) {
    return std::nullopt;
  }
  FcVariant v;
  v.name.assign(p.begin(), p.begin() + 4);   // no terminator on the wire
  return v;
}

std::optional<FcVersion> decode_fc_version(const Payload & p)
{
  if (p.size() < 3) {
    return std::nullopt;
  }
  FcVersion v;
  v.version_major = p[0];
  v.version_minor = p[1];
  v.version_patch = p[2];
  return v;
}

std::optional<Rangefinder> decode_rangefinder(const Payload & p)
{
  if (p.size() < 4) {
    return std::nullopt;
  }
  Rangefinder r;
  r.raw_cm = i32(p, 0);
  if (r.raw_cm > 0) {
    r.state = Rangefinder::State::VALID;
    r.distance_m = r.raw_cm / 100.0;
  } else if (r.raw_cm == -1) {
    r.state = Rangefinder::State::OUT_OF_RANGE;
  } else {
    // 0 is what INAV sends with no rangefinder configured (the value is never
    // written), and its MSP rangefinder driver turns a reading of 0 into -1,
    // so 0 is not a distance. The Python script reads it as a valid 0.0 m.
    // INAV 9.1.0 sends no negative other than -1; if one shows up, it is not
    // a distance either.
    r.state = Rangefinder::State::NO_READING;
  }
  return r;
}

std::optional<Attitude> decode_attitude(const Payload & p)
{
  if (p.size() < 6) {
    return std::nullopt;
  }
  Attitude a;
  a.roll = i16(p, 0) * 0.1 * DEG;
  a.pitch = i16(p, 2) * 0.1 * DEG;
  // The team's notes have yaw as int16. INAV sends a heading wrapped to
  // 0..359, never negative, so it is read unsigned.
  a.yaw = u16(p, 4) * DEG;
  return a;
}

std::optional<Status> decode_status(const Payload & p)
{
  // 22 bytes on INAV 9.1.0, where the mode bitmask is two 32-bit words. A
  // build with more modes would grow the bitmask and move the mixer profile.
  if (p.size() < 22) {
    return std::nullopt;
  }
  Status s;
  s.cycle_time_us = u16(p, 0);
  s.i2c_errors = u16(p, 2);
  s.sensors = u16(p, 4);
  s.cpu_load_pct = u16(p, 6);
  s.pid_profile = p[8] & 0x0F;
  s.battery_profile = p[8] >> 4;
  s.arming_flags = u32(p, 9);
  s.box_mode_flags = u32(p, 13) | (static_cast<uint64_t>(u32(p, 17)) << 32);
  s.mixer_profile = p[21];
  return s;
}

std::optional<OpticalFlow> decode_optical_flow(const Payload & p)
{
  if (p.size() < 9) {
    return std::nullopt;
  }
  // The team's notes say the rates are signed values written unsigned. The
  // source differs: INAV passes a float in deg/s straight to a uint16
  // parameter, and in the captures no rate is ever negative, even with the
  // gyro swinging both ways, so negatives seem to arrive as 0. Reading int16
  // is still right for every value that can occur, and gives the true rate
  // on a build that wraps negatives instead.
  OpticalFlow f;
  f.quality = p[0];
  f.flow_rate_x = i16(p, 1) * DEG;
  f.flow_rate_y = i16(p, 3) * DEG;
  f.body_rate_x = i16(p, 5) * DEG;
  f.body_rate_y = i16(p, 7) * DEG;
  return f;
}

std::optional<Analog> decode_analog(const Payload & p)
{
  if (p.size() < 24) {
    return std::nullopt;
  }
  Analog a;
  a.full_when_plugged_in = p[0] & 0x01;
  a.uses_capacity_thresholds = p[0] & 0x02;
  a.battery_state = (p[0] >> 2) & 0x03;
  a.cell_count = p[0] >> 4;
  a.voltage_v = u16(p, 1) / 100.0;
  a.current_a = i16(p, 3) / 100.0;
  // Power and the two drawn counters are int32 in INAV. The Python script
  // reads them unsigned, which turns a negative current into a huge power.
  a.power_w = i32(p, 5) / 100.0;
  a.mah_drawn = i32(p, 9);
  a.mwh_drawn = i32(p, 13);
  a.remaining_capacity = u32(p, 17);
  a.battery_pct = p[21];
  a.rssi = u16(p, 22);
  return a;
}

std::optional<LocalPose> decode_local_pose(const Payload & p)
{
  if (p.size() < 24) {
    return std::nullopt;
  }
  LocalPose l;
  l.roll = i16(p, 0) * 0.1 * DEG;
  l.pitch = i16(p, 2) * 0.1 * DEG;
  l.yaw = i16(p, 4) * 0.1 * DEG;
  // Position and velocity are interleaved per axis: cm, then cm/s.
  l.x = i32(p, 6) / 100.0;
  l.vx = i16(p, 10) / 100.0;
  l.y = i32(p, 12) / 100.0;
  l.vy = i16(p, 16) / 100.0;
  l.z = i32(p, 18) / 100.0;
  l.vz = i16(p, 22) / 100.0;
  return l;
}
}  // namespace inav
