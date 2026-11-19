// MSP v2 framing and a request/response client.
#pragma once

#include <cstdint>
#include <optional>
#include <vector>

#include "msp/transport.hpp"

namespace msp {

using Payload = std::vector<uint8_t>;

uint8_t crc8_dvb_s2(const uint8_t* data, size_t len);
Payload build_frame_v2(uint16_t cmd, const Payload& payload);

struct Frame {
    uint16_t cmd;
    bool ok;           // '>' reply; false for '!' (FC rejected the command)
    Payload payload;
};

// Incremental parser: feed it bytes as they arrive, pull complete frames out.
class FrameParser {
public:
    void feed(const uint8_t* data, size_t len);
    std::optional<Frame> next();

private:
    std::vector<uint8_t> buf_;
};

struct Reply {
    enum class Status { Ok, Error, Timeout };
    Status status;
    Payload payload;
};

class Client {
public:
    explicit Client(Transport& transport) : transport_(transport) {}

    // Sends one request and waits for the reply to that command.
    Reply request(uint16_t cmd, const Payload& payload = {}, int timeout_ms = 400);
    // Fire-and-forget (for commands such as MSP_SET_RAW_RC later on).
    void send(uint16_t cmd, const Payload& payload = {});

    Transport& transport() { return transport_; }

private:
    Transport& transport_;
    FrameParser parser_;
};

}  // namespace msp
