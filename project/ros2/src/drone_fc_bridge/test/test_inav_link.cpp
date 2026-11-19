// The TCP link against a fake FC on localhost that answers with frames
// captured from the real drone, and can drop replies, send rubbish, go silent
// with the connection open (what killed the gap10 rate run), or hang up. It
// records the sticks it is sent (MSP_SET_RAW_RC) and acks them as INAV does.

#include <gtest/gtest.h>

#include <netinet/in.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

#include <atomic>
#include <chrono>
#include <functional>
#include <map>
#include <mutex>
#include <set>
#include <string>
#include <thread>
#include <vector>

#include "capture.hpp"
#include "inav_link.hpp"
#include "msp.hpp"

namespace
{
using namespace std::chrono_literals;

Bytes make_reply(uint16_t cmd, const Bytes & payload)
{
  Bytes out{'$', 'X', '>', 0, static_cast<uint8_t>(cmd & 0xFF), static_cast<uint8_t>(cmd >> 8),
    static_cast<uint8_t>(payload.size() & 0xFF), static_cast<uint8_t>(payload.size() >> 8)};
  out.insert(out.end(), payload.begin(), payload.end());
  out.push_back(msp::crc8_dvb_s2(out.data() + 3, out.size() - 3));
  return out;
}

struct FakeOptions
{
  std::string variant{"INAV"};
  int batch{1};               // answer only once this many requests are waiting
  int drop_every{0};          // drop every n-th reply
  bool garbage{false};        // rubbish before every reply
  int silent_after{-1};       // first connection only: stop answering, stay connected
  int close_after{-1};        // first connection only: hang up after this many replies
};

class FakeFc
{
public:
  explicit FakeFc(FakeOptions options)
  : options_(std::move(options))
  {
    // The first good reply to each command in flat_still.jsonl. Parsed, not
    // copied: a damaged MSP_BOXNAMES line can hold an older complete reply.
    for (const auto & l : load_capture("flat_still")) {
      msp::Parser parser;
      parser.feed(l.frame.data(), l.frame.size());
      const auto frame = parser.next();
      const auto cmd = static_cast<uint16_t>(l.cmd);
      if (l.ok && frame && frame->cmd == cmd && !frame->is_error && !replies_.count(cmd)) {
        replies_[cmd] = make_reply(cmd, frame->payload);
      }
    }
    replies_[msp::MSP_SET_RAW_RC] = make_reply(msp::MSP_SET_RAW_RC, {});   // INAV's ack
    if (options_.variant != "INAV") {
      replies_[msp::MSP_FC_VARIANT] =
        make_reply(msp::MSP_FC_VARIANT, Bytes(options_.variant.begin(), options_.variant.end()));
    }
    listen_fd_ = socket(AF_INET, SOCK_STREAM, 0);
    int one = 1;
    setsockopt(listen_fd_, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
    sockaddr_in addr{};
    addr.sin_family = AF_INET;
    addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    bind(listen_fd_, reinterpret_cast<sockaddr *>(&addr), sizeof(addr));
    socklen_t len = sizeof(addr);
    getsockname(listen_fd_, reinterpret_cast<sockaddr *>(&addr), &len);
    port_ = ntohs(addr.sin_port);
    listen(listen_fd_, 4);
    thread_ = std::thread([this]() {serve();});
  }

  ~FakeFc()
  {
    stop_ = true;
    thread_.join();
    close(listen_fd_);
  }

  uint16_t port() const {return port_;}
  int connections() const {return connections_;}
  std::set<uint16_t> seen() const
  {
    std::lock_guard<std::mutex> lock(mutex_);
    return seen_;
  }
  int count(uint16_t cmd) const
  {
    std::lock_guard<std::mutex> lock(mutex_);
    return counts_.count(cmd) ? counts_.at(cmd) : 0;
  }
  // The payload of every MSP_SET_RAW_RC received, in order.
  std::vector<Bytes> sticks() const
  {
    std::lock_guard<std::mutex> lock(mutex_);
    return sticks_;
  }

private:
  bool wait_readable(int fd)
  {
    pollfd p{fd, POLLIN, 0};
    return poll(&p, 1, 20) > 0;
  }

  void serve()
  {
    while (!stop_) {
      if (!wait_readable(listen_fd_)) {
        continue;
      }
      const int fd = accept(listen_fd_, nullptr, nullptr);
      ++connections_;
      talk(fd, connections_ == 1);
      close(fd);
    }
  }

  // Requests are "$X<", flag, cmd, size, payload, crc: 9 bytes plus the payload.
  void talk(int fd, bool first)
  {
    Bytes in;
    std::vector<uint16_t> waiting;
    int replied = 0;
    while (!stop_) {
      if (!wait_readable(fd)) {
        continue;
      }
      uint8_t buf[256];
      const ssize_t n = recv(fd, buf, sizeof(buf), 0);
      if (n <= 0) {
        return;
      }
      in.insert(in.end(), buf, buf + n);
      while (in.size() >= 9) {
        EXPECT_EQ(Bytes(in.begin(), in.begin() + 3), (Bytes{'$', 'X', '<'}));
        const auto cmd = static_cast<uint16_t>(in[4] | (in[5] << 8));
        const std::size_t size = in[6] | (in[7] << 8);
        if (in.size() < 9 + size) {
          break;
        }
        EXPECT_EQ(in[8 + size], msp::crc8_dvb_s2(in.data() + 3, 5 + size));
        {
          std::lock_guard<std::mutex> lock(mutex_);
          seen_.insert(cmd);
          ++counts_[cmd];
          if (cmd == msp::MSP_SET_RAW_RC) {
            sticks_.emplace_back(in.begin() + 8, in.begin() + 8 + size);
          } else {
            EXPECT_EQ(size, 0u) << "a read with a payload: " << cmd;
          }
        }
        in.erase(in.begin(), in.begin() + 9 + size);
        waiting.push_back(cmd);
      }
      if (static_cast<int>(waiting.size()) < options_.batch) {
        continue;
      }
      for (uint16_t cmd : waiting) {
        if (first && options_.close_after >= 0 && replied >= options_.close_after) {
          return;
        }
        if (first && options_.silent_after >= 0 && replied >= options_.silent_after) {
          continue;
        }
        ++replied;
        if (options_.drop_every > 0 && replied % options_.drop_every == 0) {
          continue;
        }
        Bytes out;
        if (options_.garbage) {
          out = {'$', 'X', 0x55, '$', 0x01, 0x02};
        }
        const auto & reply = replies_.at(cmd);
        out.insert(out.end(), reply.begin(), reply.end());
        send(fd, out.data(), out.size(), MSG_NOSIGNAL);
      }
      waiting.clear();
    }
  }

  const FakeOptions options_;
  std::map<uint16_t, Bytes> replies_;
  int listen_fd_{-1};
  uint16_t port_{0};
  std::thread thread_;
  std::atomic<bool> stop_{false};
  std::atomic<int> connections_{0};
  mutable std::mutex mutex_;
  std::set<uint16_t> seen_;
  std::map<uint16_t, int> counts_;
  std::vector<Bytes> sticks_;
};

inav::LinkConfig config_for(const FakeFc & fc)
{
  inav::LinkConfig c;
  c.host = "127.0.0.1";
  c.port = fc.port();
  c.cycle_period_s = 0.02;
  c.reply_timeout_s = 0.1;
  c.dead_after_cycles = 3;
  c.reconnect_pause_s = 0.05;
  c.battery_every = 5;
  return c;
}

struct Logs
{
  std::mutex mutex;
  std::vector<std::string> lines;
  inav::InavLink::Logger logger()
  {
    return [this](inav::InavLink::Level, const std::string & text) {
             std::lock_guard<std::mutex> lock(mutex);
             lines.push_back(text);
           };
  }
};

// Waits up to timeout for the condition on the link's state.
bool wait_for(
  const inav::InavLink & link, const std::function<bool(const inav::LinkState &)> & ok,
  std::chrono::milliseconds timeout = 3000ms)
{
  const auto until = std::chrono::steady_clock::now() + timeout;
  while (std::chrono::steady_clock::now() < until) {
    if (ok(link.state())) {
      return true;
    }
    std::this_thread::sleep_for(10ms);
  }
  return false;
}

// Reads, and the sticks only if the test set them.
void expect_only_reads(const FakeFc & fc, bool sticks_allowed = false)
{
  for (uint16_t cmd : fc.seen()) {
    EXPECT_TRUE(msp::is_read_command(cmd) || (sticks_allowed && cmd == msp::MSP_SET_RAW_RC)) << cmd;
  }
}

// The payload build_set_raw_rc puts in the frame.
Bytes stick_payload(const msp::Sticks & s)
{
  const auto frame = msp::build_set_raw_rc(s);
  return Bytes(frame.begin() + 8, frame.end() - 1);
}

msp::Sticks some_sticks()
{
  msp::Sticks s;
  s.roll = 1400;
  s.pitch = 1600;
  s.yaw = 1550;
  s.throttle = 1450;
  return s;
}
}  // namespace

TEST(InavLink, PollsAndDecodes)
{
  FakeFc fc({});
  Logs logs;
  inav::InavLink link(config_for(fc), logs.logger());
  link.start();
  ASSERT_TRUE(wait_for(link, [](const auto & s) {
      return s.status.count >= 3 && s.analog.count >= 1;
    }));
  const auto s = link.state();
  EXPECT_TRUE(s.connected);
  EXPECT_TRUE(s.link_ok);
  ASSERT_TRUE(s.version);
  EXPECT_EQ(s.version->version_major, 9);
  EXPECT_EQ(s.version->version_minor, 1);
  EXPECT_EQ(s.status.value->sensors, 0xa3);
  EXPECT_FALSE(s.status.value->armed());
  EXPECT_TRUE(s.pose.value);
  EXPECT_TRUE(s.flow.value);
  EXPECT_EQ(s.range.value->state, inav::Rangefinder::State::NO_READING);
  EXPECT_NEAR(s.analog.value->voltage_v, 16.2, 0.1);
  EXPECT_EQ(s.connects, 1u);
  EXPECT_EQ(s.missed, 0u);
  // Battery only every 5th cycle.
  EXPECT_LT(s.analog.count * 3, s.status.count + 3);
  ASSERT_TRUE(s.rc.value);
  EXPECT_EQ(s.rc.value->throttle(), 885);
  ASSERT_TRUE(s.motors.value);
  EXPECT_EQ(s.motors.value->us, (std::vector<uint16_t>{1000, 1000, 1000, 1000}));
  ASSERT_TRUE(s.boxes);
  EXPECT_EQ(s.boxes->names.size(), 31u);
  EXPECT_EQ(s.rc_override_active(), false);   // the captures' status: only FAILSAFE on
  EXPECT_FALSE(s.sending_sticks);
  EXPECT_EQ(s.sticks_sent, 0u);
  link.stop();
  expect_only_reads(fc);
  EXPECT_TRUE(fc.sticks().empty());
  EXPECT_EQ(fc.seen(), (std::set<uint16_t>{msp::MSP_FC_VARIANT, msp::MSP_FC_VERSION,
      msp::MSP_SONAR_ALTITUDE, msp::MSP_RC, msp::MSP_MOTOR, msp::MSP_BOXNAMES, msp::MSP2_INAV_STATUS,
      msp::MSP2_INAV_OPTICAL_FLOW, msp::MSP2_INAV_ANALOG, msp::MSP2_INAV_FULL_LOCAL_POSE}));
}

TEST(InavLink, AsksForTheModeListUntilItHasOne)
{
  FakeFc fc({});
  Logs logs;
  inav::InavLink link(config_for(fc), logs.logger());
  link.start();
  ASSERT_TRUE(wait_for(link, [](const auto & s) {return s.status.count >= 30;}));
  link.stop();
  // Cycle 0 asks and gets it; the list doesn't change while the FC runs.
  EXPECT_EQ(fc.count(msp::MSP_BOXNAMES), 1);
  EXPECT_GE(fc.count(msp::MSP_RC), 30);   // MSP_RC every cycle
  EXPECT_TRUE(link.state().boxes == std::nullopt);   // forgotten with the connection
}

TEST(InavLink, SendsTheSticksEveryCycleWhileTheyAreFresh)
{
  FakeFc fc({});
  Logs logs;
  inav::InavLink link(config_for(fc), logs.logger());   // a cycle every 20 ms
  link.start();
  ASSERT_TRUE(wait_for(link, [](const auto & s) {return s.link_ok;}));
  const auto sticks = some_sticks();
  const int cycles_before = fc.count(msp::MSP2_INAV_STATUS);
  const auto until = std::chrono::steady_clock::now() + 1s;
  while (std::chrono::steady_clock::now() < until) {
    link.set_sticks(sticks);   // like the node's 20 Hz tick, but faster
    std::this_thread::sleep_for(10ms);
  }
  const auto s = link.state();
  link.stop();
  const int cycles = fc.count(msp::MSP2_INAV_STATUS) - cycles_before;
  EXPECT_TRUE(s.sending_sticks);
  ASSERT_TRUE(s.last_sticks);
  EXPECT_EQ(s.last_sticks->pitch, 1600);
  EXPECT_EQ(s.missed, 0u);          // every frame acked
  EXPECT_EQ(s.error_frames, 0u);
  const auto got = fc.sticks();
  // One stick frame per cycle (a status request each); the first cycle can
  // start just before the first set_sticks, the last after the loop ends.
  EXPECT_GT(cycles, 10);
  EXPECT_NEAR(static_cast<int>(got.size()), cycles, 1);
  EXPECT_EQ(got.size(), s.sticks_sent);
  for (const auto & p : got) {
    EXPECT_EQ(p, stick_payload(sticks));
  }
  expect_only_reads(fc, true);
}

TEST(InavLink, StopsSendingWhenTheSticksGoStale)
{
  // A node that stalls stops refreshing them: no more frames, so INAV goes
  // back to the radio.
  FakeFc fc({});
  Logs logs;
  auto c = config_for(fc);
  c.sticks_max_age_s = 0.1;
  inav::InavLink link(c, logs.logger());
  link.start();
  ASSERT_TRUE(wait_for(link, [](const auto & s) {return s.link_ok;}));
  link.set_sticks(some_sticks());
  ASSERT_TRUE(wait_for(link, [](const auto & s) {return s.sticks_sent >= 1;}));
  EXPECT_TRUE(wait_for(link, [](const auto & s) {return !s.sending_sticks;}, 500ms));
  const auto sent = fc.sticks().size();
  EXPECT_LE(sent, 7u);   // 0.1 s of 20 ms cycles, and a cycle in flight
  std::this_thread::sleep_for(300ms);
  EXPECT_EQ(fc.sticks().size(), sent);
  link.stop();
}

TEST(InavLink, StopsSendingAtOnceOnNullopt)
{
  FakeFc fc({});
  Logs logs;
  auto c = config_for(fc);
  c.sticks_max_age_s = 10.0;
  inav::InavLink link(c, logs.logger());
  link.start();
  link.set_sticks(some_sticks());
  ASSERT_TRUE(wait_for(link, [](const auto & s) {return s.sticks_sent >= 3;}));
  link.set_sticks(std::nullopt);
  ASSERT_TRUE(wait_for(link, [](const auto & s) {return !s.sending_sticks;}, 500ms));
  const auto sent = fc.sticks().size();
  std::this_thread::sleep_for(200ms);
  EXPECT_EQ(fc.sticks().size(), sent);
  link.stop();
}

TEST(InavLink, NoSticksWhileTheLinkIsDown)
{
  // The bridge hangs up: nothing is sent until the link is back, and the
  // mode list is asked for again on the new connection.
  FakeOptions o;
  o.close_after = 12;
  FakeFc fc(o);
  Logs logs;
  auto c = config_for(fc);
  c.sticks_max_age_s = 10.0;
  c.reconnect_pause_s = 0.3;
  inav::InavLink link(c, logs.logger());
  link.start();
  link.set_sticks(some_sticks());
  ASSERT_TRUE(wait_for(link, [](const auto & s) {return !s.connected && s.connects == 1;}));
  EXPECT_FALSE(link.state().sending_sticks);
  EXPECT_FALSE(link.state().boxes);
  const auto sent = fc.sticks().size();
  std::this_thread::sleep_for(150ms);   // within the reconnect pause
  EXPECT_EQ(fc.sticks().size(), sent);
  ASSERT_TRUE(wait_for(link, [](const auto & s) {
      return s.connects == 2 && s.sending_sticks && s.boxes;
    }));
  link.stop();
}

TEST(InavLink, ModeOnFromTheStatusBit)
{
  inav::LinkState s;
  EXPECT_FALSE(s.rc_override_active());   // nothing known yet
  s.boxes = inav::BoxNames{{"ARM", "ANGLE", "MSP RC OVERRIDE"}};
  EXPECT_FALSE(s.rc_override_active());   // no status yet
  s.status.value = inav::Status{};
  EXPECT_EQ(s.rc_override_active(), false);
  s.status.value->box_mode_flags = 1u << 2;
  EXPECT_EQ(s.rc_override_active(), true);
  s.boxes = inav::BoxNames{{"ARM", "ANGLE"}};   // a build without the mode
  EXPECT_FALSE(s.rc_override_active());
}

TEST(InavLink, SendsTheCycleAtOnce)
{
  // This FC answers only once 4 requests are waiting: a client that waits for
  // each reply before the next request would never get past the first one.
  FakeOptions o;
  o.batch = 4;
  FakeFc fc(o);
  Logs logs;
  inav::InavLink link(config_for(fc), logs.logger());
  link.start();
  // Startup sends 2 requests; they wait until its retry adds 2 more.
  EXPECT_TRUE(wait_for(link, [](const auto & s) {return s.status.count >= 3;}));
  link.stop();
  expect_only_reads(fc);
}

TEST(InavLink, SurvivesDroppedRepliesAndRubbish)
{
  FakeOptions o;
  o.drop_every = 3;
  o.garbage = true;
  FakeFc fc(o);
  Logs logs;
  inav::InavLink link(config_for(fc), logs.logger());
  link.start();
  ASSERT_TRUE(wait_for(link, [](const auto & s) {return s.status.count >= 10;}));
  const auto s = link.state();
  EXPECT_GT(s.missed, 0u);
  EXPECT_EQ(s.connects, 1u);   // a lost reply is not a dead link
  link.stop();
  expect_only_reads(fc);
}

TEST(InavLink, ReconnectsWhenTheLinkGoesSilent)
{
  // The gap10 rate run: no replies, connection still open.
  FakeOptions o;
  o.silent_after = 12;
  FakeFc fc(o);
  Logs logs;
  inav::InavLink link(config_for(fc), logs.logger());
  link.start();
  ASSERT_TRUE(wait_for(link, [](const auto & s) {return s.connects >= 2 && s.link_ok;}));
  const auto before = link.state().status.count;
  EXPECT_TRUE(wait_for(link, [before](const auto & s) {return s.status.count > before + 3;}));
  link.stop();
  EXPECT_EQ(fc.connections(), 2);
  bool logged = false;
  for (const auto & line : logs.lines) {
    logged |= line.find("reconnecting") != std::string::npos;
  }
  EXPECT_TRUE(logged);
}

TEST(InavLink, ReconnectsWhenTheBridgeHangsUp)
{
  FakeOptions o;
  o.close_after = 12;
  FakeFc fc(o);
  Logs logs;
  inav::InavLink link(config_for(fc), logs.logger());
  link.start();
  ASSERT_TRUE(wait_for(link, [](const auto & s) {return s.connects >= 2 && s.link_ok;}));
  link.stop();
}

TEST(InavLink, StopsWhenTheFcIsNotInav)
{
  FakeOptions o;
  o.variant = "BTFL";
  FakeFc fc(o);
  Logs logs;
  inav::InavLink link(config_for(fc), logs.logger());
  link.start();
  ASSERT_TRUE(wait_for(link, [](const auto & s) {return s.wrong_firmware;}));
  std::this_thread::sleep_for(200ms);
  const auto s = link.state();
  EXPECT_FALSE(s.link_ok);
  EXPECT_EQ(s.status.count, 0u);
  EXPECT_EQ(fc.seen(), (std::set<uint16_t>{msp::MSP_FC_VARIANT, msp::MSP_FC_VERSION}));
  EXPECT_EQ(fc.connections(), 1);
  link.stop();
}

TEST(InavLink, StopIsPromptWithNothingListening)
{
  inav::LinkConfig c;
  c.host = "127.0.0.1";
  {
    FakeFc fc({});
    c.port = fc.port();
  }   // the port is closed again: every connect is refused
  c.reconnect_pause_s = 5.0;
  Logs logs;
  inav::InavLink link(c, logs.logger());
  link.start();
  std::this_thread::sleep_for(100ms);
  const auto start = std::chrono::steady_clock::now();
  link.stop();
  EXPECT_LT(std::chrono::steady_clock::now() - start, 500ms);
  EXPECT_FALSE(link.state().connected);
  EXPECT_EQ(logs.lines.size(), 1u);   // the failure is logged once, not per retry
}
