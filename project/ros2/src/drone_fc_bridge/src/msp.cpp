#include "msp.hpp"

#include <stdexcept>
#include <string>

namespace msp
{
namespace
{
constexpr std::size_t HEADER = 8;   // "$X" dir, flag, cmd, size
constexpr std::size_t OVERHEAD = HEADER + 1;   // plus the crc

uint16_t le16(const uint8_t * p)
{
  return static_cast<uint16_t>(p[0] | (p[1] << 8));
}
}  // namespace

uint8_t crc8_dvb_s2(const uint8_t * data, std::size_t n, uint8_t crc)
{
  for (std::size_t i = 0; i < n; ++i) {
    crc ^= data[i];
    for (int bit = 0; bit < 8; ++bit) {
      crc = static_cast<uint8_t>((crc & 0x80) ? (crc << 1) ^ 0xD5 : crc << 1);
    }
  }
  return crc;
}

bool is_read_command(uint16_t cmd)
{
  switch (cmd) {
    case MSP_API_VERSION:
    case MSP_FC_VARIANT:
    case MSP_FC_VERSION:
    case MSP_SONAR_ALTITUDE:
    case MSP_ATTITUDE:
    case MSP2_INAV_STATUS:
    case MSP2_INAV_OPTICAL_FLOW:
    case MSP2_INAV_ANALOG:
    case MSP2_INAV_FULL_LOCAL_POSE:
      return true;
    default:
      return false;
  }
}

std::vector<uint8_t> build_request(uint16_t cmd, const std::vector<uint8_t> & payload)
{
  // Safety: this is the only place a request is built, and it only builds the
  // reads on the list. A write (MSP_SET_RAW_RC 200 moves the sticks, others
  // change settings) can then never leave the laptop, whatever the code that
  // calls this gets wrong. A new command has to be added to the list on purpose.
  if (!is_read_command(cmd)) {
    throw std::invalid_argument(
            "MSP command " + std::to_string(cmd) + " is not on the read-only list");
  }
  if (payload.size() > MAX_REQUEST_PAYLOAD) {
    throw std::invalid_argument("MSP request payload too long for the FC");
  }
  const auto size = static_cast<uint16_t>(payload.size());
  std::vector<uint8_t> out{'$', 'X', '<', 0,
    static_cast<uint8_t>(cmd & 0xFF), static_cast<uint8_t>(cmd >> 8),
    static_cast<uint8_t>(size & 0xFF), static_cast<uint8_t>(size >> 8)};
  out.insert(out.end(), payload.begin(), payload.end());
  out.push_back(crc8_dvb_s2(out.data() + 3, out.size() - 3));
  return out;
}

void Parser::feed(const uint8_t * data, std::size_t n)
{
  buf_.erase(buf_.begin(), buf_.begin() + head_);
  head_ = 0;
  buf_.insert(buf_.end(), data, data + n);
}

std::optional<Frame> Parser::next()
{
  const std::size_t n = buf_.size();
  std::size_t i = head_;   // everything before i is dropped when we return

  while (i < n) {
    if (buf_[i] != '$') {
      ++i;
      continue;
    }
    // A '$' at the end may be the start of a header still arriving: keep it.
    if (n - i < 3) {
      if (n - i == 2 && buf_[i + 1] != 'X') {
        ++i;
        continue;
      }
      break;
    }
    const uint8_t dir = buf_[i + 2];
    // Requests ("$X<") are not for us; anything else is garbage.
    if (buf_[i + 1] != 'X' || (dir != '>' && dir != '!')) {
      ++i;
      continue;
    }
    if (n - i < HEADER) {
      break;
    }
    const std::size_t size = le16(&buf_[i + 6]);
    // When a header can't be trusted (impossible size, or bad CRC below) we
    // step one byte past its '$' and scan again, instead of dropping the
    // length it claims. On this link a damaged reply has bytes missing from
    // the middle and the next reply follows straight after, inside the span
    // the damaged header claims. Dropping the span would lose that good reply.
    if (size > MAX_PAYLOAD) {
      ++i;
      continue;
    }
    if (n - i < OVERHEAD + size) {
      break;
    }
    if (crc8_dvb_s2(&buf_[i + 3], HEADER - 3 + size) != buf_[i + HEADER + size]) {
      ++bad_crc_;
      ++i;
      continue;
    }
    Frame frame;
    frame.cmd = le16(&buf_[i + 4]);
    frame.is_error = dir == '!';
    frame.payload.assign(buf_.begin() + i + HEADER, buf_.begin() + i + HEADER + size);
    // Move past the frame instead of erasing it: erasing from the front per
    // frame makes draining a big backlog quadratic. feed() compacts.
    skipped_ += i - head_;
    head_ = i + OVERHEAD + size;
    return frame;
  }

  skipped_ += i - head_;
  buf_.erase(buf_.begin(), buf_.begin() + i);
  head_ = 0;
  return std::nullopt;
}

void Parser::skip_pending()
{
  if (head_ < buf_.size()) {
    ++head_;
    ++skipped_;
  }
}

void Parser::reset()
{
  buf_.clear();
  head_ = 0;
}
}  // namespace msp
