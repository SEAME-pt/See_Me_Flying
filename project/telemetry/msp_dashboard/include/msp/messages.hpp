// MSP message IDs, decoded structs and translation tables.
// Layouts follow INAV 9.1.0 src/main/fc/fc_msp.c (same as inav_telemetry.py).
// Verify against fc_msp.c when INAV is upgraded.
#pragma once

#include <array>
#include <cstdint>
#include <optional>
#include <stdexcept>
#include <string>
#include <vector>

#include "msp/client.hpp"

namespace msp {

namespace cmd {
constexpr uint16_t API_VERSION = 1;
constexpr uint16_t FC_VARIANT = 2;
constexpr uint16_t FC_VERSION = 3;
constexpr uint16_t BOARD_INFO = 4;
constexpr uint16_t NAME = 10;
constexpr uint16_t SONAR_ALTITUDE = 58;
constexpr uint16_t RAW_IMU = 102;
constexpr uint16_t MOTOR = 104;
constexpr uint16_t RC = 105;
constexpr uint16_t ATTITUDE = 108;
constexpr uint16_t ALTITUDE = 109;
constexpr uint16_t BOXNAMES = 116;
constexpr uint16_t NAV_STATUS = 121;
constexpr uint16_t SET_RAW_RC = 200;
constexpr uint16_t SET_MOTOR = 214;
constexpr uint16_t INAV_STATUS = 0x2000;
constexpr uint16_t INAV_OPTICAL_FLOW = 0x2001;
constexpr uint16_t INAV_ANALOG = 0x2002;
constexpr uint16_t INAV_LINK_STATS = 0x2103;
constexpr uint16_t INAV_FULL_LOCAL_POSE = 0x2220;
}  // namespace cmd

struct DecodeError : std::runtime_error {
    using std::runtime_error::runtime_error;
};

// ---------- decoded messages (SI units / degrees) ----------

struct ApiVersion { int protocol, major, minor; };

struct BoardInfo {
    std::string board_id;
    int hardware_revision;
    bool osd;
    bool has_vcp;
    std::string target;
};

struct Attitude { double roll_deg, pitch_deg, heading_deg; };

struct Altitude { double alt_m, vario_ms; };

struct RawImu {
    std::array<double, 3> acc_g;      // INAV sends acc * 512 (1 g = 512)
    std::array<double, 3> gyro_dps;   // deg/s
    std::array<int, 3> mag;           // raw units
};

struct InavStatus {
    int cycle_time_us, i2c_errors, cpu_load_pct;
    uint16_t sensor_bits;
    bool hardware_ok;
    int pid_profile, battery_profile;
    std::optional<int> mixer_profile;
    uint32_t arming_flags;
    std::vector<uint8_t> mode_mask;   // bit i = MSP_BOXNAMES entry i
    bool armed() const { return arming_flags >> 2 & 1; }
};

struct InavAnalog {
    double voltage_v, current_a, power_w;
    int32_t mah_drawn, mwh_drawn;     // int32 in INAV, like power
    uint32_t remaining_capacity;
    int battery_pct, cell_count, battery_state;   // state: 0 ok .. 3 not present
    bool full_when_plugged_in, uses_capacity_thresholds;
    double rssi_pct;
};

struct OpticalFlow {
    int quality;                       // 0-255
    int flow_x_dps, flow_y_dps, body_x_dps, body_y_dps;
};

struct Rangefinder {
    int32_t raw_cm;                    // 0 = no rangefinder running, -1 = out of range
    bool valid() const { return raw_cm > 0; }
    double distance_m() const { return raw_cm / 100.0; }
};

struct LocalPose {
    double roll_deg, pitch_deg, yaw_deg;
    std::array<double, 3> pos_m;       // INAV works in cm
    std::array<double, 3> vel_ms;      // and cm/s
};

struct NavStatus { int mode, state, wp_action, wp_number, error, heading_target_deg; };

struct LinkStats { int rssi_dbm, link_quality_pct, snr_db; };

// ---------- decoders (throw DecodeError on short payloads) ----------

ApiVersion decode_api_version(const Payload& p);
std::string decode_text(const Payload& p);
std::string decode_fc_version(const Payload& p);
BoardInfo decode_board_info(const Payload& p);
std::vector<std::string> decode_box_names(const Payload& p);
Attitude decode_attitude(const Payload& p);
Altitude decode_altitude(const Payload& p);
RawImu decode_raw_imu(const Payload& p);
std::vector<uint16_t> decode_u16_list(const Payload& p);
InavStatus decode_inav_status(const Payload& p);
InavAnalog decode_inav_analog(const Payload& p);
OpticalFlow decode_optical_flow(const Payload& p);
Rangefinder decode_rangefinder(const Payload& p);
LocalPose decode_local_pose(const Payload& p);
NavStatus decode_nav_status(const Payload& p);
LinkStats decode_link_stats(const Payload& p);

// ---------- encoders (for the future ROS -> drone direction) ----------

Payload encode_set_raw_rc(const std::vector<uint16_t>& channels);
// MSP_SET_MOTOR: INAV reads 8 x uint16 and uses them as the motor outputs
// while disarmed (the Configurator's motor test).
Payload encode_set_motor(const std::array<uint16_t, 8>& values);

// ---------- translations ----------

std::vector<std::string> sensor_names(uint16_t sensor_bits);
// Arming blockers: every set flag except "armed" and "was ever armed".
// Bit numbers come from INAV's armingFlag_e and can change between versions.
std::vector<std::string> arming_blockers(uint32_t arming_flags);
std::vector<std::string> active_modes(const std::vector<uint8_t>& mask,
                                      const std::vector<std::string>& box_names);
const char* battery_state_name(int state);
std::string nav_mode_name(int mode);
std::string nav_state_name(int state);
std::string nav_error_name(int error);
std::string wp_action_name(int action);

}  // namespace msp
