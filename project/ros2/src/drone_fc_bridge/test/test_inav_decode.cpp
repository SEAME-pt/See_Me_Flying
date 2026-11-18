// INAV payload decoders against frames captured from the real drone. The
// expected values were worked out from the captures with struct.unpack and
// agree with telemetry/inav_telemetry.py, except where a comment says so.

#include <gtest/gtest.h>

#include <string>

#include "capture.hpp"
#include "inav_decode.hpp"
#include "msp.hpp"

namespace
{
const double DEG = 3.14159265358979323846 / 180.0;
const double EPS = 1e-9;

// Payload of a captured reply frame, after checking it is the message we think.
Bytes payload(const std::string & frame_hex, uint16_t cmd)
{
  const Bytes bytes = from_hex(frame_hex);
  msp::Parser parser;
  parser.feed(bytes.data(), bytes.size());
  const auto frame = parser.next();
  if (!frame || frame->cmd != cmd || frame->is_error) {
    ADD_FAILURE() << "not a good frame of command " << cmd << ": " << frame_hex;
    return {};
  }
  return frame->payload;
}

// Each decoder must refuse every length below its layout and accept more.
template<typename Decoder>
void expect_needs(Decoder decode, std::size_t size)
{
  for (std::size_t n = 0; n < size; ++n) {
    EXPECT_FALSE(decode(Bytes(n, 0x01))) << n << " bytes";
  }
  EXPECT_TRUE(decode(Bytes(size, 0x01)));
  EXPECT_TRUE(decode(Bytes(size + 5, 0x01)));   // newer firmware appends fields
}

Bytes le16(int v)
{
  return {static_cast<uint8_t>(v & 0xFF), static_cast<uint8_t>((v >> 8) & 0xFF)};
}

Bytes le32(int64_t v)
{
  return {static_cast<uint8_t>(v & 0xFF), static_cast<uint8_t>((v >> 8) & 0xFF),
    static_cast<uint8_t>((v >> 16) & 0xFF), static_cast<uint8_t>((v >> 24) & 0xFF)};
}

Bytes join(std::initializer_list<Bytes> parts)
{
  Bytes out;
  for (const auto & p : parts) {
    out.insert(out.end(), p.begin(), p.end());
  }
  return out;
}
}  // namespace

TEST(Decode, ApiVersion)
{
  const auto v = inav::decode_api_version(payload("24583e0001000300000205a6", 1));
  ASSERT_TRUE(v);
  EXPECT_EQ(v->protocol, 0);
  EXPECT_EQ(v->api_major, 2);
  EXPECT_EQ(v->api_minor, 5);
  expect_needs(inav::decode_api_version, 3);
}

TEST(Decode, FcVariant)
{
  const auto v = inav::decode_fc_variant(payload("24583e0002000400494e415694", 2));
  ASSERT_TRUE(v);
  EXPECT_EQ(v->name, "INAV");
  expect_needs(inav::decode_fc_variant, 4);
}

TEST(Decode, FcVersion)
{
  const auto v = inav::decode_fc_version(payload("24583e000300030009010008", 3));
  ASSERT_TRUE(v);
  EXPECT_EQ(v->version_major, 9);
  EXPECT_EQ(v->version_minor, 1);
  EXPECT_EQ(v->version_patch, 0);
  expect_needs(inav::decode_fc_version, 3);
}

TEST(Decode, RangefinderFromCaptures)
{
  // No rangefinder fitted: 0 cm in every file, which is not a distance.
  // (The Python script calls this valid, 0.0 m.)
  const auto r = inav::decode_rangefinder(payload("24583e003a0004000000000079", 58));
  ASSERT_TRUE(r);
  EXPECT_EQ(r->state, inav::Rangefinder::State::NO_READING);
  EXPECT_EQ(r->raw_cm, 0);
  expect_needs(inav::decode_rangefinder, 4);
}

TEST(Decode, RangefinderStates)
{
  using State = inav::Rangefinder::State;

  auto r = inav::decode_rangefinder(le32(123));   // what the MTF-02P will send
  ASSERT_TRUE(r);
  EXPECT_EQ(r->state, State::VALID);
  EXPECT_EQ(r->raw_cm, 123);
  EXPECT_NEAR(r->distance_m, 1.23, EPS);

  r = inav::decode_rangefinder(le32(1));
  ASSERT_TRUE(r);
  EXPECT_EQ(r->state, State::VALID);
  EXPECT_NEAR(r->distance_m, 0.01, EPS);

  r = inav::decode_rangefinder({0xFF, 0xFF, 0xFF, 0xFF});
  ASSERT_TRUE(r);
  EXPECT_EQ(r->state, State::OUT_OF_RANGE);
  EXPECT_EQ(r->raw_cm, -1);

  for (int raw : {-2, -3, -100000}) {
    r = inav::decode_rangefinder(le32(raw));
    ASSERT_TRUE(r);
    EXPECT_EQ(r->state, State::NO_READING) << raw;
    EXPECT_EQ(r->raw_cm, raw);
  }
}

TEST(Decode, Attitude)
{
  struct Golden {const char * hex; double roll_deg, pitch_deg, yaw_deg;};
  for (const auto & g : {
      Golden{"24583e006c000600f7ffc0ff300089", -0.9, -6.4, 48},     // flat_still 142
      Golden{"24583e006c000600ddffbfff01001d", -3.5, -6.5, 1},      // radio_off 142
      Golden{"24583e006c000600d20188ff650184", 46.6, -12.0, 357},   // tilted 143
      Golden{"24583e006c0006002d007dff090011", 4.5, -13.1, 9}})     // flow_moving 142
  {
    const auto a = inav::decode_attitude(payload(g.hex, 108));
    ASSERT_TRUE(a) << g.hex;
    EXPECT_NEAR(a->roll, g.roll_deg * DEG, EPS) << g.hex;
    EXPECT_NEAR(a->pitch, g.pitch_deg * DEG, EPS) << g.hex;
    EXPECT_NEAR(a->yaw, g.yaw_deg * DEG, EPS) << g.hex;
  }
  expect_needs(inav::decode_attitude, 6);
}

TEST(Decode, AttitudeLimits)
{
  // Roll goes to +-180.0 deg, pitch to +-90.0, yaw to 359.
  const auto a = inav::decode_attitude(join({le16(-1800), le16(900), le16(359)}));
  ASSERT_TRUE(a);
  EXPECT_NEAR(a->roll, -180.0 * DEG, EPS);
  EXPECT_NEAR(a->pitch, 90.0 * DEG, EPS);
  EXPECT_NEAR(a->yaw, 359.0 * DEG, EPS);
}

TEST(Decode, Status)
{
  // flat_still 123
  auto s = inav::decode_status(
    payload("24583e0000201600ff013200a3000d00000002041000000200000000000007", 0x2000));
  ASSERT_TRUE(s);
  EXPECT_EQ(s->cycle_time_us, 511);
  EXPECT_EQ(s->i2c_errors, 50);
  EXPECT_EQ(s->sensors, 0x00a3);
  EXPECT_EQ(s->cpu_load_pct, 13);
  EXPECT_EQ(s->pid_profile, 0);
  EXPECT_EQ(s->battery_profile, 0);
  EXPECT_EQ(s->arming_flags, 0x10040200u);
  EXPECT_EQ(s->box_mode_flags, 0x20000u);   // bit 17: FAILSAFE on this drone
  EXPECT_EQ(s->mixer_profile, 0);
  EXPECT_FALSE(s->armed());
  // Blocked by sensors calibrating (9), no RC link (18) and no prearm (28).
  EXPECT_EQ(s->arming_blockers(), (1u << 9) | (1u << 18) | (1u << 28));
  EXPECT_FALSE(s->rangefinder_present());
  EXPECT_TRUE(s->opflow_present());
  EXPECT_TRUE(s->hardware_ok());

  // tilted 123: "not level" (8) as well
  s = inav::decode_status(
    payload("24583e0000201600f8013200a3000e00000003041000000200000000000057", 0x2000));
  ASSERT_TRUE(s);
  EXPECT_EQ(s->cycle_time_us, 504);
  EXPECT_EQ(s->cpu_load_pct, 14);
  EXPECT_EQ(s->arming_flags, 0x10040300u);
  EXPECT_EQ(s->arming_blockers(), (1u << 8) | (1u << 9) | (1u << 18) | (1u << 28));

  // radio_off 124 and flow_moving 125
  s = inav::decode_status(
    payload("24583e0000201600f9013200a3000d0000000204100000020000000000009d", 0x2000));
  ASSERT_TRUE(s);
  EXPECT_EQ(s->cycle_time_us, 505);
  EXPECT_EQ(s->arming_flags, 0x10040200u);
  s = inav::decode_status(
    payload("24583e000020160002023200a3000d000000000410000002000000000000ec", 0x2000));
  ASSERT_TRUE(s);
  EXPECT_EQ(s->cycle_time_us, 514);
  EXPECT_EQ(s->arming_flags, 0x10040000u);

  expect_needs(inav::decode_status, 22);
}

TEST(Decode, StatusInEveryCapture)
{
  // On the bench: no rangefinder fitted, optical flow present, never armed.
  int seen = 0;
  for (const char * file : CAPTURE_FILES) {
    for (const auto & l : load_capture(file)) {
      if (!l.ok || l.cmd != msp::MSP2_INAV_STATUS) {
        continue;
      }
      SCOPED_TRACE(std::string(file) + " line " + std::to_string(l.line));
      const auto s = inav::decode_status(Bytes(l.frame.begin() + 8, l.frame.end() - 1));
      ASSERT_TRUE(s);
      ++seen;
      EXPECT_EQ(s->sensors, 0xa3);
      EXPECT_FALSE(s->rangefinder_present());
      EXPECT_TRUE(s->opflow_present());
      EXPECT_TRUE(s->hardware_ok());
      EXPECT_FALSE(s->armed());
      EXPECT_EQ(s->i2c_errors, 50);
      EXPECT_EQ(s->box_mode_flags, 0x20000u);
    }
  }
  EXPECT_EQ(seen, 19 + 14 + 16 + 16);
}

TEST(Decode, StatusHandBuilt)
{
  // Armed, with a rangefinder, a hardware failure, and every field distinct.
  const Bytes p = join({le16(1000), le16(7), le16(0x8010), le16(42), {0x21},
        le32(0x0000000C), le32(0x80000001), le32(0x00000002), {3}});
  ASSERT_EQ(p.size(), 22u);
  const auto s = inav::decode_status(p);
  ASSERT_TRUE(s);
  EXPECT_EQ(s->cycle_time_us, 1000);
  EXPECT_EQ(s->i2c_errors, 7);
  EXPECT_EQ(s->sensors, 0x8010);
  EXPECT_EQ(s->cpu_load_pct, 42);
  EXPECT_EQ(s->pid_profile, 1);
  EXPECT_EQ(s->battery_profile, 2);
  EXPECT_EQ(s->arming_flags, 0x0Cu);
  EXPECT_EQ(s->box_mode_flags, 0x0000000280000001u);
  EXPECT_EQ(s->mixer_profile, 3);
  EXPECT_TRUE(s->armed());
  EXPECT_EQ(s->arming_blockers(), 0u);   // armed and was-ever-armed are not blockers
  EXPECT_TRUE(s->rangefinder_present());
  EXPECT_FALSE(s->opflow_present());
  EXPECT_FALSE(s->hardware_ok());

  // Simulator modes (bits 4, 5) and the unused bit 17 are not blockers either.
  Bytes q = p;
  q[9] = 0x30; q[10] = 0x00; q[11] = 0x02; q[12] = 0x00;
  const auto t = inav::decode_status(q);
  ASSERT_TRUE(t);
  EXPECT_FALSE(t->armed());
  EXPECT_EQ(t->arming_blockers(), 0u);
}

TEST(Decode, OpticalFlow)
{
  // Still: flat_still 222 (the same frame is in all four files).
  auto f = inav::decode_optical_flow(payload("24583e0001200900640000000000000000c2", 0x2001));
  ASSERT_TRUE(f);
  EXPECT_EQ(f->quality, 100);
  EXPECT_EQ(f->flow_rate_x, 0.0);
  EXPECT_EQ(f->flow_rate_y, 0.0);
  EXPECT_EQ(f->body_rate_x, 0.0);
  EXPECT_EQ(f->body_rate_y, 0.0);

  // Moving: flow_moving 228, the fastest in the captures.
  f = inav::decode_optical_flow(payload("24583e00012009003238000900000000002e", 0x2001));
  ASSERT_TRUE(f);
  EXPECT_EQ(f->quality, 50);
  EXPECT_NEAR(f->flow_rate_x, 56 * DEG, EPS);
  EXPECT_NEAR(f->flow_rate_y, 9 * DEG, EPS);
  EXPECT_EQ(f->body_rate_x, 0.0);
  EXPECT_EQ(f->body_rate_y, 0.0);

  expect_needs(inav::decode_optical_flow, 9);
}

TEST(Decode, OpticalFlowHandBuilt)
{
  // The captures have no negative rate and no frame with all four set.
  const auto f = inav::decode_optical_flow(
    join({{35}, le16(-56), le16(9), le16(300), le16(-4)}));
  ASSERT_TRUE(f);
  EXPECT_EQ(f->quality, 35);
  EXPECT_NEAR(f->flow_rate_x, -56 * DEG, EPS);
  EXPECT_NEAR(f->flow_rate_y, 9 * DEG, EPS);
  EXPECT_NEAR(f->body_rate_x, 300 * DEG, EPS);
  EXPECT_NEAR(f->body_rate_y, -4 * DEG, EPS);
}

TEST(Decode, Analog)
{
  struct Golden
  {
    const char * hex;
    double volts, amps, watts;
    int mah, mwh, pct;
  };
  for (const auto & g : {
      // flat_still 202, radio_off 202, tilted 202, flow_moving 202
      Golden{"24583e00022018004050063e00e90300000c000000cf0000000000000052000072",
        16.16, 0.62, 10.01, 12, 207, 82},
      Golden{"24583e0002201800405f063f00030400000b000000c20000000000000056000039",
        16.31, 0.63, 10.27, 11, 194, 86},
      Golden{"24583e0002201800405b063e00f00300001c000000d201000000000000550000c7",
        16.27, 0.62, 10.08, 28, 466, 85},
      Golden{"24583e00022018004057063f00fe0300002a000000af0200000000000054000059",
        16.23, 0.63, 10.22, 42, 687, 84}})
  {
    const auto a = inav::decode_analog(payload(g.hex, 0x2002));
    ASSERT_TRUE(a) << g.hex;
    EXPECT_FALSE(a->full_when_plugged_in);
    EXPECT_FALSE(a->uses_capacity_thresholds);
    EXPECT_EQ(a->battery_state, 0);
    EXPECT_EQ(a->cell_count, 4);
    EXPECT_NEAR(a->voltage_v, g.volts, EPS) << g.hex;
    EXPECT_NEAR(a->current_a, g.amps, EPS) << g.hex;
    EXPECT_NEAR(a->power_w, g.watts, EPS) << g.hex;
    EXPECT_EQ(a->mah_drawn, g.mah) << g.hex;
    EXPECT_EQ(a->mwh_drawn, g.mwh) << g.hex;
    EXPECT_EQ(a->remaining_capacity, 0u);
    EXPECT_EQ(a->battery_pct, g.pct) << g.hex;
    EXPECT_EQ(a->rssi, 0);
  }
  expect_needs(inav::decode_analog, 24);
}

TEST(Decode, AnalogHandBuilt)
{
  // Negative current, power and drawn counters (the Python script would read
  // this power as about 42949 kW), and every flag field set.
  // flags: 3 cells, state 2 (critical), both low bits.
  const Bytes p = join({{0x3B}, le16(1110), le16(-150), le32(-1665), le32(-7), le32(-80),
        le32(0xF0000001), {17}, le16(1023)});
  ASSERT_EQ(p.size(), 24u);
  const auto a = inav::decode_analog(p);
  ASSERT_TRUE(a);
  EXPECT_TRUE(a->full_when_plugged_in);
  EXPECT_TRUE(a->uses_capacity_thresholds);
  EXPECT_EQ(a->battery_state, 2);
  EXPECT_EQ(a->cell_count, 3);
  EXPECT_NEAR(a->voltage_v, 11.10, EPS);
  EXPECT_NEAR(a->current_a, -1.50, EPS);
  EXPECT_NEAR(a->power_w, -16.65, EPS);
  EXPECT_EQ(a->mah_drawn, -7);
  EXPECT_EQ(a->mwh_drawn, -80);
  EXPECT_EQ(a->remaining_capacity, 0xF0000001u);
  EXPECT_EQ(a->battery_pct, 17);
  EXPECT_EQ(a->rssi, 1023);
}

TEST(Decode, LocalPose)
{
  struct Golden {const char * hex; double roll_deg, pitch_deg, yaw_deg;};
  for (const auto & g : {
      // flat_still 282, radio_off 284, tilted 282, flow_moving 282
      Golden{"24583e0020221800f4ffbeff6502000000000000000000000000000000000000d3",
        -1.2, -6.6, 61.3},
      Golden{"24583e0020221800eaffcbff130000000000000000000000000000000000000005",
        -2.2, -5.3, 1.9},
      Golden{"24583e0020221800bf0186ff060e0000000000000000000000000000000000001a",
        44.7, -12.2, 359.0},
      Golden{"24583e00202218002900bcff7d0100000000000000000000000000000000000066",
        4.1, -6.8, 38.1}})
  {
    const auto l = inav::decode_local_pose(payload(g.hex, 0x2220));
    ASSERT_TRUE(l) << g.hex;
    EXPECT_NEAR(l->roll, g.roll_deg * DEG, EPS) << g.hex;
    EXPECT_NEAR(l->pitch, g.pitch_deg * DEG, EPS) << g.hex;
    EXPECT_NEAR(l->yaw, g.yaw_deg * DEG, EPS) << g.hex;
    // No position estimate while disarmed on the bench.
    EXPECT_EQ(l->x, 0.0);
    EXPECT_EQ(l->y, 0.0);
    EXPECT_EQ(l->z, 0.0);
    EXPECT_EQ(l->vx, 0.0);
    EXPECT_EQ(l->vy, 0.0);
    EXPECT_EQ(l->vz, 0.0);
  }
  expect_needs(inav::decode_local_pose, 24);
}

TEST(Decode, LocalPoseHandBuilt)
{
  // Six distinct values, some negative and one beyond 16 bits, to pin the
  // interleaved order (x, vx, y, vy, z, vz) and the signs.
  const auto l = inav::decode_local_pose(
    join({le16(-12), le16(34), le16(3599),
      le32(123456), le16(-250), le32(-789), le16(15), le32(152), le16(-32768)}));
  ASSERT_TRUE(l);
  EXPECT_NEAR(l->roll, -1.2 * DEG, EPS);
  EXPECT_NEAR(l->pitch, 3.4 * DEG, EPS);
  EXPECT_NEAR(l->yaw, 359.9 * DEG, EPS);
  EXPECT_NEAR(l->x, 1234.56, EPS);
  EXPECT_NEAR(l->vx, -2.50, EPS);
  EXPECT_NEAR(l->y, -7.89, EPS);
  EXPECT_NEAR(l->vy, 0.15, EPS);
  EXPECT_NEAR(l->z, 1.52, EPS);
  EXPECT_NEAR(l->vz, -327.68, EPS);
}
