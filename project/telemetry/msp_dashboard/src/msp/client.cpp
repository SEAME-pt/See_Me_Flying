#include "msp/client.hpp"

#include <chrono>

namespace msp {

namespace {
constexpr size_t kHeader = 8;          // "$X" + direction + flag + cmd(2) + size(2)
constexpr size_t kMaxPayload = 4096;   // anything bigger is treated as garbage
}  // namespace

uint8_t crc8_dvb_s2(const uint8_t* data, size_t len) {
    uint8_t crc = 0;
    for (size_t i = 0; i < len; ++i) {
        crc ^= data[i];
        for (int bit = 0; bit < 8; ++bit)
            crc = (crc & 0x80) ? static_cast<uint8_t>((crc << 1) ^ 0xD5)
                               : static_cast<uint8_t>(crc << 1);
    }
    return crc;
}

Payload build_frame_v2(uint16_t cmd, const Payload& payload) {
    const auto size = static_cast<uint16_t>(payload.size());
    Payload frame{'$', 'X', '<', 0,
                  static_cast<uint8_t>(cmd & 0xFF), static_cast<uint8_t>(cmd >> 8),
                  static_cast<uint8_t>(size & 0xFF), static_cast<uint8_t>(size >> 8)};
    frame.insert(frame.end(), payload.begin(), payload.end());
    frame.push_back(crc8_dvb_s2(frame.data() + 3, frame.size() - 3));  // flag..payload
    return frame;
}

void FrameParser::feed(const uint8_t* data, size_t len) {
    buf_.insert(buf_.end(), data, data + len);
}

std::optional<Frame> FrameParser::next() {
    for (;;) {
        size_t start = 0;
        bool found = false;
        for (; start + 1 < buf_.size(); ++start) {
            if (buf_[start] == '$' && buf_[start + 1] == 'X') {
                found = true;
                break;
            }
        }
        if (!found) {
            // Keep a trailing '$': its 'X' may arrive in the next chunk.
            if (!buf_.empty() && buf_.back() == '$')
                buf_.erase(buf_.begin(), buf_.end() - 1);
            else
                buf_.clear();
            return std::nullopt;
        }
        buf_.erase(buf_.begin(), buf_.begin() + static_cast<long>(start));
        if (buf_.size() < kHeader) return std::nullopt;

        const uint8_t direction = buf_[2];
        const uint16_t cmd = static_cast<uint16_t>(buf_[4] | buf_[5] << 8);
        const size_t size = static_cast<size_t>(buf_[6] | buf_[7] << 8);
        if ((direction != '>' && direction != '!') || size > kMaxPayload) {
            buf_.erase(buf_.begin(), buf_.begin() + 2);  // not a reply frame, skip it
            continue;
        }
        const size_t total = kHeader + size + 1;
        if (buf_.size() < total) return std::nullopt;

        const bool crc_ok = crc8_dvb_s2(buf_.data() + 3, kHeader - 3 + size) == buf_[kHeader + size];
        Frame frame{cmd, direction == '>',
                    Payload(buf_.begin() + kHeader, buf_.begin() + static_cast<long>(kHeader + size))};
        buf_.erase(buf_.begin(), buf_.begin() + static_cast<long>(total));
        if (crc_ok) return frame;
    }
}

void Client::send(uint16_t cmd, const Payload& payload) {
    const Payload frame = build_frame_v2(cmd, payload);
    transport_.write_all(frame.data(), frame.size());
}

Reply Client::request(uint16_t cmd, const Payload& payload, int timeout_ms) {
    using namespace std::chrono;
    send(cmd, payload);
    const auto deadline = steady_clock::now() + milliseconds(timeout_ms);
    uint8_t chunk[512];
    for (;;) {
        while (auto frame = parser_.next()) {
            if (frame->cmd == cmd)  // replies to other (timed-out) requests are dropped
                return Reply{frame->ok ? Reply::Status::Ok : Reply::Status::Error,
                             std::move(frame->payload)};
        }
        const auto left = duration_cast<milliseconds>(deadline - steady_clock::now()).count();
        if (left <= 0) return Reply{Reply::Status::Timeout, {}};
        const size_t n = transport_.read_some(chunk, sizeof chunk, static_cast<int>(left));
        parser_.feed(chunk, n);
    }
}

}  // namespace msp
