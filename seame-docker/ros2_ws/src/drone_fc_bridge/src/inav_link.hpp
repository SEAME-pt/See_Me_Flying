// The TCP link to INAV through esp-link, for the inav backend. Read-only:
// every request goes through msp::build_request, which only builds reads.
// No ROS here: the node reads state() on its own timer.
//
// On its own thread: connect, check the FC is INAV, then poll in cycles. A
// cycle sends all its requests at once and matches the replies by command.
// INAV answers queued requests in order, one per 10 ms serial task run, so
// this is far faster over Wi-Fi than one request at a time (about 3 cycles/s
// at best). Its UART receive buffer is 256 bytes with no overflow guard, so a
// cycle stays small (5 requests, 45 bytes).
//
// esp-link can go silent with the TCP connection still open (the gap10 rate
// run, Nov 9), so several cycles in a row without a single reply count as a
// dead link: close and connect again. A late reply that arrives before the
// next cycle starts is dropped; one that arrives during it is taken as that
// cycle's (MSP replies carry no request id), so a value can be up to one
// cycle older than its stamp.

#ifndef INAV_LINK_HPP_
#define INAV_LINK_HPP_

#include <atomic>
#include <chrono>
#include <cstdint>
#include <functional>
#include <mutex>
#include <optional>
#include <string>
#include <thread>
#include <vector>

#include "inav_decode.hpp"
#include "msp.hpp"

namespace inav
{
using Clock = std::chrono::steady_clock;

struct LinkConfig
{
  std::string host{"192.168.4.1"};
  uint16_t port{23};                  // esp-link's transparent bridge (2323 resets the FC)
  double cycle_period_s{0.1};         // 5 requests take INAV about 50 ms to answer
  double reply_timeout_s{0.25};       // for the whole cycle's replies
  int dead_after_cycles{4};           // cycles in a row with no reply at all
  double reconnect_pause_s{1.0};
  int battery_every{5};               // MSP2_INAV_ANALOG every n-th cycle
};

template<typename T>
struct Latest
{
  std::optional<T> value;
  Clock::time_point stamp{};   // when the reply arrived
  uint64_t count{0};           // replies so far: a change means new data
};

struct LinkState
{
  bool connected{false};
  bool link_ok{false};          // connected, INAV, and the last cycle got a reply
  bool wrong_firmware{false};   // the FC isn't INAV: nothing is polled
  std::optional<FcVersion> version;
  Clock::time_point last_reply{};

  Latest<Status> status;
  Latest<LocalPose> pose;
  Latest<OpticalFlow> flow;
  Latest<Rangefinder> range;
  Latest<Analog> analog;

  uint64_t requests{0};
  uint64_t replies{0};
  uint64_t missed{0};        // requests without a reply within the timeout
  uint64_t late{0};          // replies dropped because they came after their cycle
  uint64_t error_frames{0};  // "$X!": the FC rejected a request
  uint64_t bad_crc{0};
  uint64_t connects{0};
};

class InavLink
{
public:
  enum class Level {INFO, WARN, ERROR};
  using Logger = std::function<void(Level, const std::string &)>;

  InavLink(LinkConfig config, Logger log);
  ~InavLink();   // stops the thread

  InavLink(const InavLink &) = delete;
  InavLink & operator=(const InavLink &) = delete;

  void start();
  void stop();
  LinkState state() const;

private:
  enum class Cycle {REPLIED, SILENT, CLOSED};

  void run();
  bool connect_once();
  void close_socket();
  bool startup();
  Cycle cycle(uint64_t n);
  // Takes the parsed frames, storing those still pending; late ones are counted.
  void take_frames(std::vector<uint16_t> & pending);
  void store(const msp::Frame & frame);
  bool send_all(const std::vector<uint8_t> & bytes);
  // Reads for at most until, feeding the parser. False if the connection closed.
  bool read_until(Clock::time_point until);
  void drop_stale();
  bool sleep_for(double seconds);   // false if stopping

  const LinkConfig config_;
  const Logger log_;
  int fd_{-1};
  msp::Parser parser_;
  std::thread thread_;
  std::atomic<bool> stopping_{false};
  mutable std::mutex mutex_;
  LinkState state_;
};
}  // namespace inav

#endif  // INAV_LINK_HPP_
