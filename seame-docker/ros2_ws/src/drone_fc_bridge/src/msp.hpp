// MSP v2 framing for the inav backend: build requests, parse replies.
// No ROS and no sockets here, so it can be tested against captured frames.
//
// Frame: '$' 'X' dir | flag u8 | cmd u16 | size u16 | payload[size] | crc u8
//   dir:  '<' request, '>' reply, '!' error reply
//   crc:  CRC8 DVB-S2 over flag..payload (not over "$X" and dir)
//   multi-byte fields are little-endian

#ifndef MSP_HPP_
#define MSP_HPP_

#include <cstddef>
#include <cstdint>
#include <optional>
#include <vector>

namespace msp
{
// The read commands the backend may send.
constexpr uint16_t MSP_API_VERSION = 1;
constexpr uint16_t MSP_FC_VARIANT = 2;
constexpr uint16_t MSP_FC_VERSION = 3;
constexpr uint16_t MSP_SONAR_ALTITUDE = 58;
constexpr uint16_t MSP_ATTITUDE = 108;
constexpr uint16_t MSP2_INAV_STATUS = 0x2000;
constexpr uint16_t MSP2_INAV_OPTICAL_FLOW = 0x2001;
constexpr uint16_t MSP2_INAV_ANALOG = 0x2002;
constexpr uint16_t MSP2_INAV_FULL_LOCAL_POSE = 0x2220;

// Longest reply payload the parser accepts. INAV's reply buffer is 512 bytes
// (MSP_PORT_OUTBUF_SIZE) for everything that isn't a flash download, the
// messages we poll are at most 24 bytes, and the longest reply in the captures
// (MSP_BOXNAMES) is 359. A larger limit would only make a damaged size field
// hold the stream back for longer.
constexpr std::size_t MAX_PAYLOAD = 512;

// The FC silently drops a request with a longer payload (MSP_PORT_INBUF_SIZE).
constexpr std::size_t MAX_REQUEST_PAYLOAD = 192;

uint8_t crc8_dvb_s2(const uint8_t * data, std::size_t n, uint8_t crc = 0);

// True only for the read commands listed above.
bool is_read_command(uint16_t cmd);

// Bytes of one MSP v2 request. Throws std::invalid_argument for any command
// that is not on the read list, or a payload the FC would drop.
std::vector<uint8_t> build_request(uint16_t cmd, const std::vector<uint8_t> & payload = {});

struct Frame
{
  uint16_t cmd{0};
  bool is_error{false};   // "$X!": the FC rejected the request
  std::vector<uint8_t> payload;
};

// Stream parser for what comes back from the FC. feed() bytes in any chunking,
// then call next() until it returns nullopt.
class Parser
{
public:
  void feed(const uint8_t * data, std::size_t n);

  // The next complete reply or error frame with a good CRC. Bytes before it
  // that belong to no good frame are dropped. After it returns nullopt the
  // buffer holds at most one unfinished frame (under 9 + MAX_PAYLOAD bytes),
  // so it stays bounded as long as the caller drains after each feed().
  std::optional<Frame> next();

  // Give up on the unfinished frame at the front, for the caller's reply
  // timeout: a damaged header can claim more bytes than will ever come, and
  // would hold back the good replies behind it until that many arrived. Drops
  // only that header's '$'; call next() again for the replies behind it.
  void skip_pending();

  // Drop everything buffered, good replies included. For a reconnect.
  void reset();

  std::size_t bad_crc_count() const {return bad_crc_;}
  // Bytes dropped that were not part of a returned frame (reset() not counted).
  std::size_t skipped_bytes() const {return skipped_;}
  std::size_t buffered() const {return buf_.size() - head_;}

private:
  std::vector<uint8_t> buf_;
  std::size_t head_{0};   // start of what next() hasn't consumed yet
  std::size_t bad_crc_{0};
  std::size_t skipped_{0};
};
}  // namespace msp

#endif  // MSP_HPP_
