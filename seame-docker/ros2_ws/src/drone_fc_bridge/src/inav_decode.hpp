// Decoders for the INAV MSP replies the inav backend reads. Layouts are from
// the INAV 9.1.0 source (src/main/fc/fc_msp.c) and checked against captures
// from the drone.
//
// Each decoder returns nullopt when the payload is shorter than the layout.
// A longer payload is accepted: newer firmware appends fields.
//
// Units are SI (m, m/s, V, A, W, rad, rad/s). Axes, signs and frames are
// INAV's own, NOT ROS's; converting them is the backend's job:
//   roll   positive right side down
//   pitch  positive nose down
//   yaw    a compass heading, 0 to 2 pi, growing clockwise seen from above
//   local pose position and velocity: earth frame NEU (x north, y east, z up)
//   optical flow rates: about the body X and Y axes

#ifndef INAV_DECODE_HPP_
#define INAV_DECODE_HPP_

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

namespace inav
{
using Payload = std::vector<uint8_t>;

// Sensor bits in Status::sensors (packSensorStatus). A set bit means the
// sensor was detected at start-up, not that its data is fresh.
constexpr uint16_t SENSOR_ACC = 1u << 0;
constexpr uint16_t SENSOR_BARO = 1u << 1;
constexpr uint16_t SENSOR_MAG = 1u << 2;
constexpr uint16_t SENSOR_GPS = 1u << 3;
constexpr uint16_t SENSOR_RANGEFINDER = 1u << 4;
constexpr uint16_t SENSOR_OPFLOW = 1u << 5;
constexpr uint16_t SENSOR_PITOT = 1u << 6;
constexpr uint16_t SENSOR_TEMP = 1u << 7;
constexpr uint16_t SENSOR_HARDWARE_FAILURE = 1u << 15;

// Bits in Status::arming_flags (armingFlag_e in fc/runtime_config.h).
constexpr uint32_t ARMING_ARMED = 1u << 2;
constexpr uint32_t ARMING_WAS_EVER_ARMED = 1u << 3;
// The reasons arming is blocked: bits 6-16 and 18-30 (ARMING_DISABLED_ALL_FLAGS).
// Bits 4 and 5 are simulator modes, not blockers, and bit 17 is unused; the
// Python telemetry script lists those as blockers too.
constexpr uint32_t ARMING_BLOCKERS = 0x7FFDFFC0u;

struct ApiVersion   // MSP_API_VERSION (1)
{
  uint8_t protocol{0};
  uint8_t api_major{0};
  uint8_t api_minor{0};
};

struct FcVariant   // MSP_FC_VARIANT (2)
{
  std::string name;   // 4 characters, "INAV"
};

struct FcVersion   // MSP_FC_VERSION (3)
{
  uint8_t version_major{0};
  uint8_t version_minor{0};
  uint8_t version_patch{0};
};

// MSP_SONAR_ALTITUDE (58). The caller must also check the rangefinder bit in
// Status::sensors: nothing in this message says a sensor exists. And a sensor
// that stops sending leaves its last distance here; INAV does not mark it stale.
struct Rangefinder
{
  enum class State
  {
    VALID,          // distance_m holds a reading
    OUT_OF_RANGE,   // -1: out of range, tilted too far, failed, or no reading yet
    NO_READING,     // 0 or another negative: no rangefinder running
  };
  State state{State::NO_READING};
  int32_t raw_cm{0};
  double distance_m{0.0};   // tilt-corrected by INAV; only meaningful when VALID
};

struct Attitude   // MSP_ATTITUDE (108)
{
  double roll{0.0};    // rad, 0.1 deg steps
  double pitch{0.0};   // rad, 0.1 deg steps
  double yaw{0.0};     // rad, whole degrees on the wire (0..359)
};

struct Status   // MSP2_INAV_STATUS (0x2000)
{
  uint16_t cycle_time_us{0};
  uint16_t i2c_errors{0};
  uint16_t sensors{0};          // SENSOR_* bits
  uint16_t cpu_load_pct{0};
  uint8_t pid_profile{0};       // profiles count from 0 here; the configurator shows +1
  uint8_t battery_profile{0};
  uint32_t arming_flags{0};     // ARMING_* bits
  uint64_t box_mode_flags{0};   // bit n: the n-th name in MSP_BOXNAMES is active
  uint8_t mixer_profile{0};

  bool armed() const {return arming_flags & ARMING_ARMED;}
  uint32_t arming_blockers() const {return arming_flags & ARMING_BLOCKERS;}
  bool rangefinder_present() const {return sensors & SENSOR_RANGEFINDER;}
  bool opflow_present() const {return sensors & SENSOR_OPFLOW;}
  bool hardware_ok() const {return !(sensors & SENSOR_HARDWARE_FAILURE);}
};

// MSP2_INAV_OPTICAL_FLOW (0x2001). On this firmware negative rates do not
// survive the wire (see the decoder), so expect only the positive half of
// each axis.
struct OpticalFlow
{
  uint8_t quality{0};       // 0..100 with the MSP flow sensor; flow reads 0 while it is low
  double flow_rate_x{0.0};  // rad/s, whole deg/s on the wire
  double flow_rate_y{0.0};
  double body_rate_x{0.0};  // rad/s, gyro averaged over the same interval
  double body_rate_y{0.0};
};

struct Analog   // MSP2_INAV_ANALOG (0x2002)
{
  bool full_when_plugged_in{false};
  bool uses_capacity_thresholds{false};
  uint8_t battery_state{0};   // 0 ok, 1 warning, 2 critical, 3 not present
  uint8_t cell_count{0};
  double voltage_v{0.0};
  double current_a{0.0};
  double power_w{0.0};
  int32_t mah_drawn{0};
  int32_t mwh_drawn{0};
  uint32_t remaining_capacity{0};   // mAh or mWh, per INAV's battery_capacity_unit
  uint8_t battery_pct{0};
  uint16_t rssi{0};                 // raw, as INAV reports it
};

struct LocalPose   // MSP2_INAV_FULL_LOCAL_POSE (0x2220)
{
  double roll{0.0};    // rad
  double pitch{0.0};   // rad
  double yaw{0.0};     // rad, 0.1 deg steps here (whole degrees in Attitude)
  double x{0.0}, y{0.0}, z{0.0};      // m, NEU
  double vx{0.0}, vy{0.0}, vz{0.0};   // m/s, NEU; 0 while INAV has no estimate
};

std::optional<ApiVersion> decode_api_version(const Payload & p);
std::optional<FcVariant> decode_fc_variant(const Payload & p);
std::optional<FcVersion> decode_fc_version(const Payload & p);
std::optional<Rangefinder> decode_rangefinder(const Payload & p);
std::optional<Attitude> decode_attitude(const Payload & p);
std::optional<Status> decode_status(const Payload & p);
std::optional<OpticalFlow> decode_optical_flow(const Payload & p);
std::optional<Analog> decode_analog(const Payload & p);
std::optional<LocalPose> decode_local_pose(const Payload & p);
}  // namespace inav

#endif  // INAV_DECODE_HPP_
