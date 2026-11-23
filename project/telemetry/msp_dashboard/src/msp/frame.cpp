#include "msp/frame.hpp"

#include <cstdio>
#include <map>

namespace msp {

RawFrame make_request_v2(uint16_t cmd, const Payload& payload) {
    RawFrame f;
    f.version = 2;
    f.direction = '<';
    f.cmd = cmd;
    f.payload = payload;
    f.bytes = build_frame_v2(cmd, payload);
    return f;
}

std::optional<RawFrame> StreamParser::next() {
    constexpr size_t kMaxPayload = 4096;
    for (;;) {
        // Skip to the next "$M" or "$X".
        size_t i = 0;
        for (; i < buf_.size(); ++i) {
            if (buf_[i] != '$') continue;
            if (i + 1 == buf_.size()) break;                 // '$' at the end: wait for more
            if (buf_[i + 1] == 'M' || buf_[i + 1] == 'X') break;
        }
        if (i > 0) {
            garbage_ += i;
            buf_.erase(buf_.begin(), buf_.begin() + static_cast<long>(i));
        }
        if (buf_.size() < 3) return std::nullopt;

        const char direction = static_cast<char>(buf_[2]);
        if (directions_.find(direction) == std::string::npos) {
            buf_.erase(buf_.begin());   // not a frame we expect here: resync
            continue;
        }

        RawFrame f;
        f.direction = direction;
        size_t total = 0;
        bool ok = false;

        if (buf_[1] == 'M') {   // v1: $M<dir> size cmd payload xor-checksum
            if (buf_.size() < 5) return std::nullopt;
            const size_t size = buf_[3];
            total = 5 + size + 1;
            if (buf_.size() < total) return std::nullopt;
            uint8_t sum = 0;
            for (size_t k = 3; k < 5 + size; ++k) sum ^= buf_[k];
            ok = sum == buf_[5 + size];
            f.version = 1;
            f.cmd = buf_[4];
            f.payload.assign(buf_.begin() + 5, buf_.begin() + static_cast<long>(5 + size));
        } else {                // v2: $X<dir> flag cmd16 size16 payload crc8
            if (buf_.size() < 8) return std::nullopt;
            const size_t size = static_cast<size_t>(buf_[6] | buf_[7] << 8);
            if (size > kMaxPayload) {
                buf_.erase(buf_.begin());
                continue;
            }
            total = 8 + size + 1;
            if (buf_.size() < total) return std::nullopt;
            ok = crc8_dvb_s2(buf_.data() + 3, 5 + size) == buf_[8 + size];
            f.version = 2;
            f.cmd = static_cast<uint16_t>(buf_[4] | buf_[5] << 8);
            f.payload.assign(buf_.begin() + 8, buf_.begin() + static_cast<long>(8 + size));
        }

        if (!ok) {
            ++bad_crc_;
            buf_.erase(buf_.begin());   // drop the '$' and look for the next frame
            continue;
        }
        f.bytes.assign(buf_.begin(), buf_.begin() + static_cast<long>(total));
        buf_.erase(buf_.begin(), buf_.begin() + static_cast<long>(total));
        return f;
    }
}

std::string command_name(uint16_t cmd) {
    static const std::map<uint16_t, const char*> kNames = {
        {1, "MSP_API_VERSION"}, {2, "MSP_FC_VARIANT"}, {3, "MSP_FC_VERSION"},
        {4, "MSP_BOARD_INFO"}, {5, "MSP_BUILD_INFO"}, {10, "MSP_NAME"}, {11, "MSP_SET_NAME"},
        {34, "MSP_MODE_RANGES"}, {35, "MSP_SET_MODE_RANGE"}, {36, "MSP_FEATURE"},
        {37, "MSP_SET_FEATURE"}, {54, "MSP_CF_SERIAL_CONFIG"}, {58, "MSP_SONAR_ALTITUDE"},
        {64, "MSP_RX_MAP"}, {65, "MSP_SET_RX_MAP"}, {68, "MSP_REBOOT"},
        {70, "MSP_DATAFLASH_SUMMARY"}, {101, "MSP_STATUS"}, {102, "MSP_RAW_IMU"},
        {103, "MSP_SERVO"}, {104, "MSP_MOTOR"}, {105, "MSP_RC"}, {106, "MSP_RAW_GPS"},
        {107, "MSP_COMP_GPS"}, {108, "MSP_ATTITUDE"}, {109, "MSP_ALTITUDE"},
        {110, "MSP_ANALOG"}, {111, "MSP_RC_TUNING"}, {112, "MSP_PID"}, {116, "MSP_BOXNAMES"},
        {117, "MSP_PIDNAMES"}, {118, "MSP_WP"}, {119, "MSP_BOXIDS"}, {121, "MSP_NAV_STATUS"},
        {150, "MSP_STATUS_EX"}, {200, "MSP_SET_RAW_RC"}, {201, "MSP_SET_RAW_GPS"},
        {202, "MSP_SET_PID"}, {204, "MSP_SET_RC_TUNING"}, {205, "MSP_ACC_CALIBRATION"},
        {206, "MSP_MAG_CALIBRATION"}, {209, "MSP_SET_WP"}, {214, "MSP_SET_MOTOR"},
        {250, "MSP_EEPROM_WRITE"},
        {0x1003, "MSP2_COMMON_SETTING"}, {0x1004, "MSP2_COMMON_SET_SETTING"},
        {0x2000, "MSP2_INAV_STATUS"}, {0x2001, "MSP2_INAV_OPTICAL_FLOW"},
        {0x2002, "MSP2_INAV_ANALOG"}, {0x2003, "MSP2_INAV_MISC"}, {0x2004, "MSP2_INAV_SET_MISC"},
        {0x2103, "MSP2_INAV_GET_LINK_STATS"}, {0x2220, "MSP2_INAV_FULL_LOCAL_POSE"},
    };
    const auto it = kNames.find(cmd);
    if (it != kNames.end()) return it->second;
    char buf[16];
    std::snprintf(buf, sizeof buf, "cmd 0x%04X", cmd);
    return buf;
}

bool is_write_command(uint16_t cmd) {
    if (cmd >= 200 && cmd <= 255) return true;   // MSP_SET_*, calibrations, EEPROM write
    if (cmd == 68) return true;                   // MSP_REBOOT
    return command_name(cmd).find("SET") != std::string::npos;
}

}  // namespace msp
