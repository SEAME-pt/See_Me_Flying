// MSP v2 framing against the frames captured from the real drone (test/data).

#include <gtest/gtest.h>

#include <chrono>
#include <map>
#include <stdexcept>
#include <string>
#include <utility>
#include <vector>

#include "capture.hpp"
#include "msp.hpp"

namespace
{
// A good reply: MSP_ATTITUDE from flat_still.jsonl line 142.
const char ATTITUDE_HEX[] = "24583e006c000600f7ffc0ff300089";
const uint16_t MSP_ALTITUDE = 109;          // not ours: stale replies in the captures
const uint16_t MSP_BOXNAMES = 116;
const uint16_t MSP_SET_RAW_RC = 200;
const uint16_t MSP2_INAV_GET_LINK_STATS = 0x2103;

void feed(msp::Parser & parser, const Bytes & bytes)
{
  parser.feed(bytes.data(), bytes.size());
}

std::vector<msp::Frame> drain(msp::Parser & parser)
{
  std::vector<msp::Frame> out;
  while (auto frame = parser.next()) {
    out.push_back(*frame);
  }
  return out;
}

std::vector<msp::Frame> parse(const Bytes & bytes)
{
  msp::Parser parser;
  feed(parser, bytes);
  return drain(parser);
}

Bytes payload_of(const Bytes & frame)
{
  return Bytes(frame.begin() + 8, frame.end() - 1);
}

// A frame with a correct CRC, any direction and command.
Bytes make_frame(char dir, uint16_t cmd, const Bytes & payload)
{
  Bytes out{'$', 'X', static_cast<uint8_t>(dir), 0,
    static_cast<uint8_t>(cmd & 0xFF), static_cast<uint8_t>(cmd >> 8),
    static_cast<uint8_t>(payload.size() & 0xFF), static_cast<uint8_t>(payload.size() >> 8)};
  out.insert(out.end(), payload.begin(), payload.end());
  out.push_back(msp::crc8_dvb_s2(out.data() + 3, out.size() - 3));
  return out;
}

Bytes operator+(Bytes a, const Bytes & b)
{
  a.insert(a.end(), b.begin(), b.end());
  return a;
}

// The complete good frame found inside a damaged MSP_BOXNAMES reply, after
// the point where bytes went missing: a stale reply to an earlier request.
// {file, line} -> frame hex. flat_still line 106 is damaged too but holds none.
const std::map<std::pair<std::string, int>, std::string> EMBEDDED = {
  {{"flat_still", 109}, "24583e000321030000000006"},
  {{"flat_still", 115}, "24583e006d000a00000000000000430000005a"},
  {{"radio_off", 117}, "24583e006d000a0000000000000010000000fc"},
};

// The intact MSP_BOXNAMES reply (368 bytes), flat_still.jsonl line 107.
Bytes good_boxnames()
{
  for (const auto & l : load_capture("flat_still")) {
    if (l.line == 107) {
      return l.frame;
    }
  }
  return {};
}
}  // namespace

TEST(Crc, StandardCheckValue)
{
  const std::string s = "123456789";
  EXPECT_EQ(msp::crc8_dvb_s2(reinterpret_cast<const uint8_t *>(s.data()), s.size()), 0xBC);
  EXPECT_EQ(msp::crc8_dvb_s2(nullptr, 0), 0x00);
}

TEST(Crc, MatchesCapturedFrames)
{
  // API_VERSION, ATTITUDE, INAV_STATUS: the CRC covers flag..payload.
  for (const char * hex : {"24583e0001000300000205a6", ATTITUDE_HEX,
      "24583e0000201600ff013200a3000d00000002041000000200000000000007"})
  {
    const Bytes f = from_hex(hex);
    EXPECT_EQ(msp::crc8_dvb_s2(f.data() + 3, f.size() - 4), f.back()) << hex;
  }
}

TEST(BuildRequest, SameBytesAsPython)
{
  // From build_frame() in telemetry/inav_telemetry.py.
  EXPECT_EQ(msp::build_request(msp::MSP_API_VERSION), from_hex("24583c000100000045"));
  EXPECT_EQ(msp::build_request(msp::MSP_ATTITUDE), from_hex("24583c006c000000d8"));
  EXPECT_EQ(msp::build_request(msp::MSP2_INAV_STATUS), from_hex("24583c000020000032"));
  EXPECT_EQ(msp::build_request(msp::MSP2_INAV_FULL_LOCAL_POSE), from_hex("24583c002022000068"));
}

TEST(BuildRequest, OnlyReadCommands)
{
  const std::vector<uint16_t> allowed = {1, 2, 3, 58, 108, 0x2000, 0x2001, 0x2002, 0x2220};
  for (uint16_t cmd : allowed) {
    EXPECT_TRUE(msp::is_read_command(cmd)) << cmd;
    EXPECT_NO_THROW(msp::build_request(cmd)) << cmd;
  }
  // Nothing else in the whole command space gets through.
  int count = 0;
  for (int cmd = 0; cmd <= 0xFFFF; ++cmd) {
    count += msp::is_read_command(static_cast<uint16_t>(cmd));
  }
  EXPECT_EQ(count, static_cast<int>(allowed.size()));

  EXPECT_THROW(msp::build_request(MSP_SET_RAW_RC), std::invalid_argument);
  // Other writes, and reads that are simply not on the list.
  for (uint16_t cmd : {0, 68 /* reboot */, 109, 116, 201, 205, 250 /* eeprom write */,
      0x2003, 0x2103, 0x1F01 /* MSP2 sensor rangefinder */, 0xFFFF})
  {
    EXPECT_FALSE(msp::is_read_command(cmd)) << cmd;
    EXPECT_THROW(msp::build_request(cmd), std::invalid_argument) << cmd;
  }
}

TEST(BuildRequest, PayloadAndItsLimit)
{
  const Bytes req = msp::build_request(msp::MSP_ATTITUDE, {0xAA, 0xBB});
  EXPECT_EQ(req, make_frame('<', msp::MSP_ATTITUDE, {0xAA, 0xBB}));
  EXPECT_NO_THROW(msp::build_request(msp::MSP_ATTITUDE, Bytes(msp::MAX_REQUEST_PAYLOAD)));
  EXPECT_THROW(
    msp::build_request(msp::MSP_ATTITUDE, Bytes(msp::MAX_REQUEST_PAYLOAD + 1)),
    std::invalid_argument);
}

TEST(Captures, EveryGoodFrameParses)
{
  // Good and damaged frames per file, so a reader that skips lines is noticed.
  const std::map<std::string, std::pair<int, int>> expected = {
    {"flat_still", {289, 3}}, {"radio_off", {274, 1}}, {"tilted", {289, 0}},
    {"flow_moving", {274, 0}}};
  for (const char * file : CAPTURE_FILES) {
    int good = 0, bad = 0;
    for (const auto & l : load_capture(file)) {
      if (l.frame.empty()) {
        continue;   // timeout
      }
      SCOPED_TRACE(std::string(file) + " line " + std::to_string(l.line));
      if (!l.ok) {
        ++bad;
        continue;
      }
      ++good;
      msp::Parser parser;
      feed(parser, l.frame);
      const auto frames = drain(parser);
      ASSERT_EQ(frames.size(), 1u);
      EXPECT_EQ(frames[0].cmd, l.cmd);
      EXPECT_FALSE(frames[0].is_error);
      EXPECT_EQ(frames[0].payload, payload_of(l.frame));
      EXPECT_EQ(parser.bad_crc_count(), 0u);
      EXPECT_EQ(parser.skipped_bytes(), 0u);
      EXPECT_EQ(parser.buffered(), 0u);
    }
    EXPECT_EQ(good, expected.at(file).first) << file;
    EXPECT_EQ(bad, expected.at(file).second) << file;
  }
}

TEST(Captures, DamagedFramesAreNotReturned)
{
  for (const char * file : CAPTURE_FILES) {
    for (const auto & l : load_capture(file)) {
      if (l.ok || l.frame.empty()) {
        continue;
      }
      SCOPED_TRACE(std::string(file) + " line " + std::to_string(l.line));
      msp::Parser parser;
      feed(parser, l.frame);
      for (const auto & frame : drain(parser)) {
        EXPECT_NE(frame.cmd, l.cmd);   // only the embedded stale reply may come out
      }
      EXPECT_EQ(parser.bad_crc_count(), 1u);
    }
  }
}

TEST(Captures, WholeFileAsOneStream)
{
  for (const char * file : CAPTURE_FILES) {
    SCOPED_TRACE(file);
    // What a parser that resyncs well must return: every good frame, plus the
    // stale reply embedded in a damaged one, in order.
    Bytes stream;
    std::vector<std::pair<int, Bytes>> expected;
    for (const auto & l : load_capture(file)) {
      stream = stream + l.frame;
      if (l.ok) {
        expected.emplace_back(l.cmd, payload_of(l.frame));
      } else if (EMBEDDED.count({file, l.line})) {
        const auto inner = parse(from_hex(EMBEDDED.at({file, l.line})));
        ASSERT_EQ(inner.size(), 1u);
        expected.emplace_back(inner[0].cmd, inner[0].payload);
      }
    }

    msp::Parser whole;
    feed(whole, stream);
    const auto at_once = drain(whole);

    msp::Parser bytewise;
    std::vector<msp::Frame> one_by_one;
    for (uint8_t b : stream) {
      bytewise.feed(&b, 1);
      for (auto & frame : drain(bytewise)) {
        one_by_one.push_back(frame);
      }
      // Drained after every feed, the buffer never holds more than one frame.
      ASSERT_LT(bytewise.buffered(), 9 + msp::MAX_PAYLOAD);
    }

    ASSERT_EQ(at_once.size(), expected.size());
    ASSERT_EQ(one_by_one.size(), expected.size());
    for (std::size_t i = 0; i < expected.size(); ++i) {
      SCOPED_TRACE("frame " + std::to_string(i));
      EXPECT_EQ(at_once[i].cmd, expected[i].first);
      EXPECT_EQ(at_once[i].payload, expected[i].second);
      EXPECT_EQ(one_by_one[i].cmd, expected[i].first);
      EXPECT_EQ(one_by_one[i].payload, expected[i].second);
    }
    EXPECT_EQ(whole.bad_crc_count(), bytewise.bad_crc_count());
    EXPECT_EQ(whole.skipped_bytes(), bytewise.skipped_bytes());
    EXPECT_EQ(whole.buffered(), bytewise.buffered());
  }
}

TEST(Captures, RecoversFrameEmbeddedInDamagedOne)
{
  const Bytes good = good_boxnames();
  ASSERT_EQ(good.size(), 368u);
  int damaged = 0;
  for (const char * file : CAPTURE_FILES) {
    for (const auto & l : load_capture(file)) {
      if (l.ok || l.frame.empty()) {
        continue;
      }
      ++damaged;
      SCOPED_TRACE(std::string(file) + " line " + std::to_string(l.line));
      ASSERT_EQ(l.cmd, MSP_BOXNAMES);
      // What happened on the wire: the reply was cut after 80 bytes, then came
      // a stale reply (in three of the four) and a fresh MSP_BOXNAMES, which
      // the capture cut off at the 368 bytes the first header claimed.
      const bool has_embedded = EMBEDDED.count({file, l.line}) > 0;
      const Bytes embedded = has_embedded ? from_hex(EMBEDDED.at({file, l.line})) : Bytes();
      const std::size_t rest = l.frame.size() - 80 - embedded.size();
      ASSERT_EQ(
        l.frame,
        Bytes(good.begin(), good.begin() + 80) + embedded +
        Bytes(good.begin(), good.begin() + rest));

      msp::Parser parser;
      feed(parser, l.frame);
      auto frames = drain(parser);
      if (has_embedded) {
        ASSERT_EQ(frames.size(), 1u);
        EXPECT_EQ(frames[0].cmd, embedded[4] | (embedded[5] << 8));
        EXPECT_EQ(frames[0].payload, payload_of(embedded));
      } else {
        EXPECT_TRUE(frames.empty());
      }
      // The cut-off fresh reply is still waiting for its missing bytes.
      EXPECT_EQ(parser.buffered(), rest);

      // The rest of that fresh reply arrives, as it would have on the wire.
      feed(parser, Bytes(good.begin() + rest, good.end()));
      frames = drain(parser);
      ASSERT_EQ(frames.size(), 1u);
      EXPECT_EQ(frames[0].cmd, MSP_BOXNAMES);
      EXPECT_EQ(frames[0].payload, payload_of(good));
      EXPECT_EQ(parser.buffered(), 0u);

      // And when it doesn't: a good frame right after the damaged one is
      // still returned, once the cut-off reply has failed its CRC too.
      msp::Parser other;
      feed(other, l.frame + good + from_hex(ATTITUDE_HEX));
      frames = drain(other);
      ASSERT_EQ(frames.size(), has_embedded ? 3u : 2u);
      EXPECT_EQ(frames[frames.size() - 2].cmd, MSP_BOXNAMES);
      EXPECT_EQ(frames[frames.size() - 2].payload, payload_of(good));
      EXPECT_EQ(frames.back().cmd, msp::MSP_ATTITUDE);
      EXPECT_EQ(other.bad_crc_count(), 2u);
    }
  }
  EXPECT_EQ(damaged, 4);
  EXPECT_EQ(MSP_ALTITUDE, parse(from_hex(EMBEDDED.at({"flat_still", 115})))[0].cmd);
  EXPECT_EQ(MSP2_INAV_GET_LINK_STATS, parse(from_hex(EMBEDDED.at({"flat_still", 109})))[0].cmd);
}

TEST(Parser, SkipsGarbageBetweenFrames)
{
  const Bytes attitude = from_hex(ATTITUDE_HEX);
  const Bytes api = from_hex("24583e0001000300000205a6");
  // Garbage that looks like the start of a header in several ways.
  const Bytes junk1 = {0x00, 0xFF, '$', '$', 'X', 'q', 0x13};
  const Bytes junk2 = {'$', 'M', '>', 0x00, '$', 'X'};
  const Bytes junk3 = {'X', '>', '$'};

  msp::Parser parser;
  feed(parser, junk1 + attitude + junk2 + api + junk3);
  const auto frames = drain(parser);
  ASSERT_EQ(frames.size(), 2u);
  EXPECT_EQ(frames[0].cmd, msp::MSP_ATTITUDE);
  EXPECT_EQ(frames[0].payload, payload_of(attitude));
  EXPECT_EQ(frames[1].cmd, msp::MSP_API_VERSION);
  EXPECT_EQ(parser.bad_crc_count(), 0u);
  // The last '$' is kept: it could be the start of the next header.
  EXPECT_EQ(parser.buffered(), 1u);
  EXPECT_EQ(parser.skipped_bytes(), junk1.size() + junk2.size() + junk3.size() - 1);
}

TEST(Parser, FrameSplitAtEveryPoint)
{
  const Bytes attitude = from_hex(ATTITUDE_HEX);
  for (std::size_t cut = 0; cut <= attitude.size(); ++cut) {
    msp::Parser parser;
    parser.feed(attitude.data(), cut);
    if (cut < attitude.size()) {
      EXPECT_FALSE(parser.next()) << cut;
    }
    parser.feed(attitude.data() + cut, attitude.size() - cut);
    const auto frames = drain(parser);
    ASSERT_EQ(frames.size(), 1u) << cut;
    EXPECT_EQ(frames[0].payload, payload_of(attitude));
    EXPECT_EQ(parser.skipped_bytes(), 0u);
  }
}

TEST(Parser, IgnoresRequestFrames)
{
  // Our own request echoed back, and somebody else's write request.
  const Bytes attitude = from_hex(ATTITUDE_HEX);
  const auto frames = parse(
    msp::build_request(msp::MSP_ATTITUDE) + attitude +
    make_frame('<', MSP_SET_RAW_RC, {1, 2, 3, 4}));
  ASSERT_EQ(frames.size(), 1u);
  EXPECT_EQ(frames[0].cmd, msp::MSP_ATTITUDE);
  EXPECT_FALSE(frames[0].is_error);
}

TEST(Parser, ErrorFrame)
{
  // INAV answers an unknown command with "$X!" and no payload.
  const auto frames = parse(make_frame('!', 0x2103, {}) + from_hex(ATTITUDE_HEX));
  ASSERT_EQ(frames.size(), 2u);
  EXPECT_EQ(frames[0].cmd, 0x2103);
  EXPECT_TRUE(frames[0].is_error);
  EXPECT_TRUE(frames[0].payload.empty());
  EXPECT_FALSE(frames[1].is_error);
}

TEST(Parser, RejectsBadCrc)
{
  Bytes bad = from_hex(ATTITUDE_HEX);
  bad[9] ^= 0x01;   // one payload bit flipped
  msp::Parser parser;
  feed(parser, bad);
  EXPECT_FALSE(parser.next());
  EXPECT_EQ(parser.bad_crc_count(), 1u);
  EXPECT_EQ(parser.skipped_bytes(), bad.size());
  EXPECT_EQ(parser.buffered(), 0u);

  feed(parser, from_hex(ATTITUDE_HEX));
  EXPECT_EQ(drain(parser).size(), 1u);
  EXPECT_EQ(parser.bad_crc_count(), 1u);
}

TEST(Parser, OversizedSizeDoesNotStall)
{
  // A header claiming 65535 bytes (and one just over the limit) must not make
  // the parser wait for them: the good frame behind it comes out at once.
  for (uint16_t size : {static_cast<uint16_t>(0xFFFF),
      static_cast<uint16_t>(msp::MAX_PAYLOAD + 1)})
  {
    const Bytes header = {'$', 'X', '>', 0, 0x74, 0x00,
      static_cast<uint8_t>(size & 0xFF), static_cast<uint8_t>(size >> 8)};
    msp::Parser parser;
    feed(parser, header + from_hex(ATTITUDE_HEX));
    const auto frames = drain(parser);
    ASSERT_EQ(frames.size(), 1u) << size;
    EXPECT_EQ(frames[0].cmd, msp::MSP_ATTITUDE);
    EXPECT_EQ(parser.buffered(), 0u);
    EXPECT_EQ(parser.skipped_bytes(), header.size());
    EXPECT_EQ(parser.bad_crc_count(), 0u);   // never got as far as a CRC
  }
}

TEST(Parser, LargestPayloadIsAccepted)
{
  Bytes payload(msp::MAX_PAYLOAD);
  for (std::size_t i = 0; i < payload.size(); ++i) {
    payload[i] = static_cast<uint8_t>(i * 7);
  }
  const auto frames = parse(make_frame('>', MSP_BOXNAMES, payload));
  ASSERT_EQ(frames.size(), 1u);
  EXPECT_EQ(frames[0].payload, payload);
}

TEST(Parser, BufferStaysBoundedOnGarbage)
{
  msp::Parser parser;
  const Bytes junk(100000, 0x55);
  feed(parser, junk);
  EXPECT_FALSE(parser.next());
  EXPECT_EQ(parser.buffered(), 0u);
  EXPECT_EQ(parser.skipped_bytes(), junk.size());
}

TEST(Parser, ResetDropsHalfFrame)
{
  const Bytes attitude = from_hex(ATTITUDE_HEX);
  msp::Parser parser;
  parser.feed(attitude.data(), 10);   // header and part of the payload, then silence
  EXPECT_FALSE(parser.next());
  EXPECT_EQ(parser.buffered(), 10u);

  parser.reset();
  EXPECT_EQ(parser.buffered(), 0u);

  // Without the reset these bytes would have completed the old header's frame.
  feed(parser, attitude);
  const auto frames = drain(parser);
  ASSERT_EQ(frames.size(), 1u);
  EXPECT_EQ(frames[0].payload, payload_of(attitude));
  EXPECT_EQ(parser.bad_crc_count(), 0u);
  EXPECT_EQ(parser.skipped_bytes(), 0u);
}

TEST(Parser, SkipPendingReleasesTheRepliesBehindIt)
{
  // The damage seen in the captures: an MSP_BOXNAMES reply cut short, with good
  // replies straight after. Its header claims 368 bytes, so they wait behind it.
  const Bytes boxnames = good_boxnames();
  ASSERT_EQ(boxnames.size(), 368u);
  const Bytes attitude = from_hex(ATTITUDE_HEX);
  const Bytes flow = make_frame('>', msp::MSP2_INAV_OPTICAL_FLOW, Bytes(9, 0));
  msp::Parser parser;
  feed(parser, Bytes(boxnames.begin(), boxnames.begin() + 80) + attitude + flow);
  EXPECT_TRUE(drain(parser).empty());

  // reset() would lose them; skip_pending() gives up on the header alone.
  parser.skip_pending();
  const auto frames = drain(parser);
  ASSERT_EQ(frames.size(), 2u);
  EXPECT_EQ(frames[0].cmd, msp::MSP_ATTITUDE);
  EXPECT_EQ(frames[1].cmd, msp::MSP2_INAV_OPTICAL_FLOW);
  EXPECT_EQ(parser.buffered(), 0u);
  EXPECT_EQ(parser.skipped_bytes(), 80u);
}

TEST(Parser, DrainsABigBacklogInLinearTime)
{
  // 2 MB of replies in one feed(): erasing per frame took seconds here.
  const Bytes attitude = from_hex(ATTITUDE_HEX);
  const std::size_t count = 2000000 / attitude.size();
  Bytes backlog;
  for (std::size_t k = 0; k < count; ++k) {
    backlog.insert(backlog.end(), attitude.begin(), attitude.end());
  }
  msp::Parser parser;
  feed(parser, backlog);
  const auto start = std::chrono::steady_clock::now();
  std::size_t frames = 0;
  while (parser.next()) {
    ++frames;
  }
  const auto took = std::chrono::steady_clock::now() - start;
  EXPECT_EQ(frames, count);
  EXPECT_EQ(parser.buffered(), 0u);
  EXPECT_LT(took, std::chrono::seconds(1));
}

TEST(Parser, FeedAfterPartialDrainKeepsOrder)
{
  // feed() compacts what next() already consumed; nothing may move or repeat.
  const Bytes a = from_hex(ATTITUDE_HEX);
  const Bytes f = make_frame('>', msp::MSP2_INAV_OPTICAL_FLOW, Bytes(9, 1));
  msp::Parser parser;
  feed(parser, a + f + Bytes(f.begin(), f.begin() + 5));
  ASSERT_TRUE(parser.next());   // a; f still buffered behind it
  feed(parser, Bytes(f.begin() + 5, f.end()));
  const auto frames = drain(parser);
  ASSERT_EQ(frames.size(), 2u);
  EXPECT_EQ(frames[0].payload, payload_of(f));
  EXPECT_EQ(frames[1].payload, payload_of(f));
  EXPECT_EQ(parser.skipped_bytes(), 0u);
}
