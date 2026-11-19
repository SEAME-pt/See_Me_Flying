#include "msp/messages.hpp"

#include <algorithm>
#include <cstring>
#include <map>
#include <type_traits>

static_assert(__BYTE_ORDER__ == __ORDER_LITTLE_ENDIAN__,
              "MSP is little-endian; this reader assumes a little-endian host (x86, Pi)");

namespace msp {

namespace {

// Reads little-endian values from a payload, throwing if it runs short.
class Reader {
public:
    explicit Reader(const Payload& p, size_t offset = 0) : p_(p), off_(offset) {}

    template <class T>
    T get() {
        static_assert(std::is_trivially_copyable_v<T>);
        if (off_ + sizeof(T) > p_.size())
            throw DecodeError("payload too short (" + std::to_string(p_.size()) + " bytes)");
        T v;
        std::memcpy(&v, p_.data() + off_, sizeof(T));
        off_ += sizeof(T);
        return v;
    }

private:
    const Payload& p_;
    size_t off_;
};

std::string clean_text(const uint8_t* begin, const uint8_t* end) {
    std::string s;
    for (const uint8_t* c = begin; c != end; ++c) {
        if (*c == 0) break;
        s += (*c >= 0x20 && *c < 0x7F) ? static_cast<char>(*c) : '?';
    }
    while (!s.empty() && s.back() == ' ') s.pop_back();
    return s;
}

std::string lookup(const std::map<int, std::string>& table, int key, const char* unknown) {
    auto it = table.find(key);
    return it != table.end() ? it->second : std::string(unknown) + " " + std::to_string(key);
}

}  // namespace

// ---------- decoders ----------

ApiVersion decode_api_version(const Payload& p) {
    Reader r(p);
    ApiVersion v{};
    v.protocol = r.get<uint8_t>();
    v.major = r.get<uint8_t>();
    v.minor = r.get<uint8_t>();
    return v;
}

std::string decode_text(const Payload& p) {
    return clean_text(p.data(), p.data() + p.size());
}

std::string decode_fc_version(const Payload& p) {
    if (p.size() < 3) throw DecodeError("payload too short");
    return std::to_string(p[0]) + "." + std::to_string(p[1]) + "." + std::to_string(p[2]);
}

BoardInfo decode_board_info(const Payload& p) {  // MSP_BOARD_INFO (4)
    Reader r(p, 4);
    BoardInfo b{};
    if (p.size() < 9) throw DecodeError("payload too short");
    b.board_id = clean_text(p.data(), p.data() + 4);
    b.hardware_revision = r.get<uint16_t>();
    b.osd = r.get<uint8_t>() == 2;
    b.has_vcp = r.get<uint8_t>() & 1;
    const size_t name_len = r.get<uint8_t>();
    const size_t end = std::min(p.size(), 9 + name_len);
    b.target = clean_text(p.data() + 9, p.data() + end);
    return b;
}

std::vector<std::string> decode_box_names(const Payload& p) {  // MSP_BOXNAMES (116)
    std::vector<std::string> names;
    std::string cur;
    for (uint8_t c : p) {
        if (c == ';') {
            if (!cur.empty()) names.push_back(cur);
            cur.clear();
        } else if (c >= 0x20 && c < 0x7F) {
            cur += static_cast<char>(c);
        }
    }
    if (!cur.empty()) names.push_back(cur);
    return names;
}

Attitude decode_attitude(const Payload& p) {  // MSP_ATTITUDE (108)
    Reader r(p);
    Attitude a{};
    a.roll_deg = r.get<int16_t>() / 10.0;
    a.pitch_deg = r.get<int16_t>() / 10.0;
    a.heading_deg = r.get<int16_t>();
    return a;
}

Altitude decode_altitude(const Payload& p) {  // MSP_ALTITUDE (109)
    Reader r(p);
    Altitude a{};
    a.alt_m = r.get<int32_t>() / 100.0;
    a.vario_ms = r.get<int16_t>() / 100.0;
    return a;
}

RawImu decode_raw_imu(const Payload& p) {  // MSP_RAW_IMU (102)
    Reader r(p);
    RawImu imu{};
    for (auto& v : imu.acc_g) v = r.get<int16_t>() / 512.0;
    for (auto& v : imu.gyro_dps) v = r.get<int16_t>();
    for (auto& v : imu.mag) v = r.get<int16_t>();
    return imu;
}

std::vector<uint16_t> decode_u16_list(const Payload& p) {  // MSP_RC (105), MSP_MOTOR (104)
    Reader r(p);
    std::vector<uint16_t> out(p.size() / 2);
    for (auto& v : out) v = r.get<uint16_t>();
    return out;
}

InavStatus decode_inav_status(const Payload& p) {  // MSP2_INAV_STATUS (0x2000)
    Reader r(p);
    InavStatus s{};
    s.cycle_time_us = r.get<uint16_t>();
    s.i2c_errors = r.get<uint16_t>();
    const uint16_t sensors = r.get<uint16_t>();
    s.cpu_load_pct = r.get<uint16_t>();
    const uint8_t profiles = r.get<uint8_t>();
    s.arming_flags = r.get<uint32_t>();

    s.sensor_bits = sensors;
    s.hardware_ok = !(sensors >> 15 & 1);
    s.pid_profile = (profiles & 0x0F) + 1;
    s.battery_profile = (profiles >> 4) + 1;

    constexpr size_t kFixed = 13;
    const size_t rest = p.size() - kFixed;
    const size_t mask_len = rest / 4 * 4;  // mode bitmask: whole 32-bit words
    s.mode_mask.assign(p.begin() + kFixed, p.begin() + static_cast<long>(kFixed + mask_len));
    if (rest > mask_len) s.mixer_profile = p[kFixed + mask_len] + 1;
    return s;
}

InavAnalog decode_inav_analog(const Payload& p) {  // MSP2_INAV_ANALOG (0x2002)
    Reader r(p);
    InavAnalog a{};
    const uint8_t flags = r.get<uint8_t>();
    a.voltage_v = r.get<uint16_t>() / 100.0;
    a.current_a = r.get<int16_t>() / 100.0;
    a.power_w = r.get<uint32_t>() / 100.0;
    a.mah_drawn = r.get<uint32_t>();
    a.mwh_drawn = r.get<uint32_t>();
    a.remaining_capacity = r.get<uint32_t>();
    a.battery_pct = r.get<uint8_t>();
    a.rssi_pct = r.get<uint16_t>() / 1023.0 * 100.0;
    a.cell_count = flags >> 4;
    a.battery_state = flags >> 2 & 3;
    a.full_when_plugged_in = flags & 1;
    a.uses_capacity_thresholds = flags >> 1 & 1;
    return a;
}

OpticalFlow decode_optical_flow(const Payload& p) {  // MSP2_INAV_OPTICAL_FLOW (0x2001)
    Reader r(p);
    OpticalFlow f{};
    f.quality = r.get<uint8_t>();
    f.flow_x_dps = r.get<int16_t>();
    f.flow_y_dps = r.get<int16_t>();
    f.body_x_dps = r.get<int16_t>();
    f.body_y_dps = r.get<int16_t>();
    return f;
}

Rangefinder decode_rangefinder(const Payload& p) {  // MSP_SONAR_ALTITUDE (58)
    Reader r(p);
    return Rangefinder{r.get<int32_t>()};
}

LocalPose decode_local_pose(const Payload& p) {  // MSP2_INAV_FULL_LOCAL_POSE (0x2220)
    Reader r(p);
    LocalPose lp{};
    lp.roll_deg = r.get<int16_t>() / 10.0;
    lp.pitch_deg = r.get<int16_t>() / 10.0;
    lp.yaw_deg = r.get<int16_t>() / 10.0;
    for (int axis = 0; axis < 3; ++axis) {   // x, vx, y, vy, z, vz
        lp.pos_m[axis] = r.get<int32_t>() / 100.0;
        lp.vel_ms[axis] = r.get<int16_t>() / 100.0;
    }
    return lp;
}

NavStatus decode_nav_status(const Payload& p) {  // MSP_NAV_STATUS (121)
    Reader r(p);
    NavStatus n{};
    n.mode = r.get<uint8_t>();
    n.state = r.get<uint8_t>();
    n.wp_action = r.get<uint8_t>();
    n.wp_number = r.get<uint8_t>();
    n.error = r.get<uint8_t>();
    n.heading_target_deg = r.get<int16_t>();
    return n;
}

LinkStats decode_link_stats(const Payload& p) {  // MSP2_INAV_GET_LINK_STATS (0x2103)
    Reader r(p);
    LinkStats l{};
    l.rssi_dbm = -static_cast<int>(r.get<uint8_t>());
    l.link_quality_pct = r.get<uint8_t>();
    l.snr_db = r.get<int8_t>();
    return l;
}

// ---------- encoders ----------

Payload encode_set_raw_rc(const std::vector<uint16_t>& channels) {
    Payload p;
    for (uint16_t ch : channels) {
        p.push_back(static_cast<uint8_t>(ch & 0xFF));
        p.push_back(static_cast<uint8_t>(ch >> 8));
    }
    return p;
}

Payload encode_set_motor(const std::array<uint16_t, 8>& values) {
    return encode_set_raw_rc(std::vector<uint16_t>(values.begin(), values.end()));  // same layout
}

// ---------- translations ----------

std::vector<std::string> sensor_names(uint16_t bits) {
    static const char* const kNames[] = {"acc", "baro", "mag", "gps",
                                         "rangefinder", "opflow", "pitot", "temp"};
    std::vector<std::string> out;
    for (int i = 0; i < 8; ++i)
        if (bits >> i & 1) out.emplace_back(kNames[i]);
    return out;
}

std::vector<std::string> arming_blockers(uint32_t flags) {
    // INAV armingFlag_e (runtime_config.h), same table as inav_telemetry.py.
    static const std::map<int, std::string> kBits = {
        {4, "simulator HITL"}, {5, "simulator SITL"}, {6, "geozone"},
        {7, "failsafe"}, {8, "not level"}, {9, "calibrating"},
        {10, "system overloaded"}, {11, "nav unsafe"}, {12, "compass not calibrated"},
        {13, "acc not calibrated"}, {14, "arm switch"}, {15, "hardware failure"},
        {16, "BOXFAILSAFE"}, {18, "no RC link"}, {19, "throttle"}, {20, "CLI"},
        {21, "CMS menu"}, {22, "OSD menu"}, {23, "roll/pitch not centered"},
        {24, "servo autotrim"}, {25, "out of memory"}, {26, "invalid setting"},
        {27, "PWM output error"}, {28, "no prearm"}, {29, "DSHOT beeper"},
        {30, "landing detected"},
    };
    std::vector<std::string> out;
    for (int i = 0; i < 32; ++i) {
        if (i == 2 || i == 3 || !(flags >> i & 1)) continue;  // armed / was ever armed
        out.push_back(lookup(kBits, i, "flag bit"));
    }
    return out;
}

std::vector<std::string> active_modes(const std::vector<uint8_t>& mask,
                                      const std::vector<std::string>& box_names) {
    std::vector<std::string> out;
    for (size_t i = 0; i < mask.size() * 8; ++i) {
        if (!(mask[i / 8] >> (i % 8) & 1)) continue;
        out.push_back(i < box_names.size() ? box_names[i] : "mode bit " + std::to_string(i));
    }
    return out;
}

const char* battery_state_name(int state) {
    static const char* const kNames[] = {"ok", "warning", "critical", "not present"};
    return state >= 0 && state < 4 ? kNames[state] : "?";
}

// MSP_NAV_STATUS codes (navigation.h, MultiWii-compatible). Verify on upgrade.
std::string nav_mode_name(int mode) {
    static const std::map<int, std::string> k = {
        {0, "none"}, {1, "hold"}, {2, "RTH"}, {3, "waypoint"}, {15, "emergency"}};
    return lookup(k, mode, "mode");
}

std::string nav_state_name(int state) {
    static const std::map<int, std::string> k = {
        {0, "none"}, {1, "RTH start"}, {2, "RTH en route"}, {3, "hold (infinite)"},
        {4, "hold (timed)"}, {5, "WP en route"}, {6, "next WP"}, {7, "WP jump"},
        {8, "land start"}, {9, "landing"}, {10, "landed"}, {11, "land settle"},
        {12, "land descent"}, {13, "hover above home"}, {14, "emergency landing"}};
    return lookup(k, state, "state");
}

std::string nav_error_name(int error) {
    static const std::map<int, std::string> k = {
        {0, "none"}, {1, "too far"}, {2, "GPS spoiled"}, {3, "WP CRC"},
        {4, "finished"}, {5, "time wait"}, {6, "invalid jump"}, {7, "invalid data"},
        {8, "waiting RTH alt"}, {9, "GPS fix lost"}, {10, "disarmed"}, {11, "landing"}};
    return lookup(k, error, "error");
}

std::string wp_action_name(int action) {
    static const std::map<int, std::string> k = {
        {0, "-"}, {1, "waypoint"}, {2, "poshold"}, {3, "poshold (timed)"},
        {4, "RTH"}, {5, "set POI"}, {6, "jump"}, {7, "set heading"}, {8, "land"}};
    return lookup(k, action, "action");
}

}  // namespace msp
