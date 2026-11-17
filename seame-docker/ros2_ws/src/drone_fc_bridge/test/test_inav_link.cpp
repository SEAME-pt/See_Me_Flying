// The TCP link against a fake FC on localhost that answers with frames
// captured from the real drone, and can drop replies, send rubbish, go silent
// with the connection open (what killed the gap10 rate run), or hang up.

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
    // The first good reply to each command in flat_still.jsonl.
    for (const auto & l : load_capture("flat_still")) {
      if (l.ok && !replies_.count(static_cast<uint16_t>(l.cmd))) {
        replies_[static_cast<uint16_t>(l.cmd)] = l.frame;
      }
    }
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

  // Requests are "$X<", flag, cmd, size 0, crc: 9 bytes each.
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
        EXPECT_EQ(in[8], msp::crc8_dvb_s2(in.data() + 3, 5));
        in.erase(in.begin(), in.begin() + 9);
        {
          std::lock_guard<std::mutex> lock(mutex_);
          seen_.insert(cmd);
        }
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

void expect_only_reads(const FakeFc & fc)
{
  for (uint16_t cmd : fc.seen()) {
    EXPECT_TRUE(msp::is_read_command(cmd)) << cmd;
  }
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
  link.stop();
  expect_only_reads(fc);
  EXPECT_EQ(fc.seen(), (std::set<uint16_t>{msp::MSP_FC_VARIANT, msp::MSP_FC_VERSION,
      msp::MSP_SONAR_ALTITUDE, msp::MSP2_INAV_STATUS, msp::MSP2_INAV_OPTICAL_FLOW,
      msp::MSP2_INAV_ANALOG, msp::MSP2_INAV_FULL_LOCAL_POSE}));
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
