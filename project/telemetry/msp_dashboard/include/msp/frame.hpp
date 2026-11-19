// Raw MSP frames in both framings, in either direction. Used by the gateway,
// which has to understand requests from any client (the dashboard speaks
// MSP v2, INAV Configurator mixes v1 and v2) and pass them through unchanged.
#pragma once

#include <cstdint>
#include <optional>
#include <string>
#include <vector>

#include "msp/client.hpp"

namespace msp {

struct RawFrame {
    int version = 2;        // 1 = "$M", 2 = "$X"
    char direction = '<';   // '<' request, '>' reply, '!' error reply
    uint16_t cmd = 0;
    Payload payload;
    Payload bytes;          // the whole frame exactly as received, for forwarding
};

// Builds a v2 request as a RawFrame (for frames the gateway sends itself).
RawFrame make_request_v2(uint16_t cmd, const Payload& payload);

class StreamParser {
public:
    // directions: which frames to accept, e.g. "<" for requests or ">!" for replies.
    explicit StreamParser(std::string directions) : directions_(std::move(directions)) {}

    void feed(const uint8_t* data, size_t len) { buf_.insert(buf_.end(), data, data + len); }
    std::optional<RawFrame> next();

    unsigned long garbage_bytes() const { return garbage_; }   // skipped between frames
    unsigned long bad_checksums() const { return bad_crc_; }

private:
    std::string directions_;
    std::vector<uint8_t> buf_;
    unsigned long garbage_ = 0, bad_crc_ = 0;
};

// "MSP_ATTITUDE", "MSP2_INAV_STATUS", or "cmd 0x1234" for unknown ones.
std::string command_name(uint16_t cmd);
// True for commands that change something on the FC (MSP_SET_*, reboot,
// EEPROM write, ...). A heuristic: v1 ids 200-255 plus names containing SET.
bool is_write_command(uint16_t cmd);

}  // namespace msp
