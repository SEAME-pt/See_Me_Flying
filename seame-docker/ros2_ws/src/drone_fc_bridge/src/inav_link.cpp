#include "inav_link.hpp"

#include <fcntl.h>
#include <netdb.h>
#include <netinet/in.h>
#include <netinet/tcp.h>
#include <poll.h>
#include <sys/socket.h>
#include <unistd.h>

#include <algorithm>
#include <cerrno>
#include <utility>

namespace inav
{
namespace
{
constexpr double CONNECT_TIMEOUT_S = 3.0;   // Wi-Fi connects can be slow
constexpr double STARTUP_TIMEOUT_S = 1.0;
constexpr int SLICE_MS = 50;                // how often a wait checks stop()

int ms_until(Clock::time_point t)
{
  const auto left = std::chrono::duration_cast<std::chrono::milliseconds>(t - Clock::now());
  return static_cast<int>(std::clamp<int64_t>(left.count(), 0, SLICE_MS));
}

Clock::duration seconds(double s)
{
  return std::chrono::duration_cast<Clock::duration>(std::chrono::duration<double>(s));
}
}  // namespace

InavLink::InavLink(LinkConfig config, Logger log)
: config_(std::move(config)), log_(std::move(log))
{
}

InavLink::~InavLink()
{
  stop();
}

void InavLink::start()
{
  if (!thread_.joinable()) {
    stopping_ = false;
    thread_ = std::thread([this]() {run();});
  }
}

void InavLink::stop()
{
  stopping_ = true;
  if (thread_.joinable()) {
    thread_.join();
  }
  close_socket();
}

LinkState InavLink::state() const
{
  std::lock_guard<std::mutex> lock(mutex_);
  return state_;
}

void InavLink::run()
{
  bool failing = false;   // log a failure to connect once, not on every retry
  while (!stopping_) {
    if (!connect_once()) {
      if (!failing) {
        log_(Level::WARN, "Cannot connect to " + config_.host + ":" +
          std::to_string(config_.port) + ": retrying every " +
          std::to_string(config_.reconnect_pause_s) + " s");
      }
      failing = true;
      sleep_for(config_.reconnect_pause_s);
      continue;
    }
    failing = false;
    if (!startup()) {
      close_socket();
      if (state().wrong_firmware) {
        return;   // polling a flight controller that isn't INAV makes no sense
      }
      sleep_for(config_.reconnect_pause_s);
      continue;
    }

    int silent = 0;
    for (uint64_t n = 0; !stopping_; ++n) {
      const auto start = Clock::now();
      const Cycle result = cycle(n);
      if (result == Cycle::CLOSED) {
        log_(Level::WARN, "Connection closed by the bridge: reconnecting");
        break;
      }
      silent = result == Cycle::SILENT ? silent + 1 : 0;
      {
        std::lock_guard<std::mutex> lock(mutex_);
        if (state_.link_ok != (silent == 0)) {
          state_.link_ok = silent == 0;
          if (state_.link_ok) {
            log_(Level::INFO, "Link up: the FC replies");
          } else {
            log_(Level::WARN, "No reply from the FC");
          }
        }
      }
      if (silent >= config_.dead_after_cycles) {
        log_(Level::WARN, "No reply in " + std::to_string(silent) +
          " cycles with the connection open: reconnecting");
        break;
      }
      std::this_thread::sleep_until(start + seconds(config_.cycle_period_s));
    }
    close_socket();
    sleep_for(config_.reconnect_pause_s);
  }
}

bool InavLink::connect_once()
{
  addrinfo hints{};
  hints.ai_family = AF_INET;
  hints.ai_socktype = SOCK_STREAM;
  addrinfo * found = nullptr;
  const auto port = std::to_string(config_.port);
  if (getaddrinfo(config_.host.c_str(), port.c_str(), &hints, &found) != 0 || !found) {
    return false;
  }
  fd_ = socket(AF_INET, SOCK_STREAM | SOCK_NONBLOCK | SOCK_CLOEXEC, 0);
  int rc = fd_ < 0 ? -1 : ::connect(fd_, found->ai_addr, found->ai_addrlen);
  freeaddrinfo(found);
  if (fd_ < 0 || (rc < 0 && errno != EINPROGRESS)) {
    close_socket();
    return false;
  }
  // Non-blocking connect: wait for it in slices, so stop() isn't held up.
  const auto deadline = Clock::now() + seconds(CONNECT_TIMEOUT_S);
  while (rc < 0) {
    if (stopping_ || Clock::now() >= deadline) {
      close_socket();
      return false;
    }
    pollfd p{fd_, POLLOUT, 0};
    if (poll(&p, 1, ms_until(deadline)) > 0) {
      int err = 0;
      socklen_t len = sizeof(err);
      getsockopt(fd_, SOL_SOCKET, SO_ERROR, &err, &len);
      if (err != 0) {
        close_socket();
        return false;
      }
      rc = 0;
    }
  }
  int one = 1;
  setsockopt(fd_, IPPROTO_TCP, TCP_NODELAY, &one, sizeof(one));
  parser_.reset();
  std::lock_guard<std::mutex> lock(mutex_);
  state_.connected = true;
  ++state_.connects;
  return true;
}

void InavLink::close_socket()
{
  if (fd_ >= 0) {
    ::close(fd_);
    fd_ = -1;
  }
  std::lock_guard<std::mutex> lock(mutex_);
  state_.connected = false;
  state_.link_ok = false;
}

bool InavLink::startup()
{
  // A reply can be lost on this link, so ask a few times before giving up.
  std::optional<FcVariant> variant;
  std::optional<FcVersion> version;
  const auto deadline = Clock::now() + seconds(STARTUP_TIMEOUT_S);
  while (!stopping_ && (!variant || !version) && Clock::now() < deadline) {
    auto request = msp::build_request(msp::MSP_FC_VARIANT);
    const auto second = msp::build_request(msp::MSP_FC_VERSION);
    request.insert(request.end(), second.begin(), second.end());
    if (!send_all(request)) {
      return false;
    }
    const auto until = std::min(deadline, Clock::now() + seconds(config_.reply_timeout_s));
    while ((!variant || !version) && Clock::now() < until) {
      if (!read_until(std::min(until, Clock::now() + std::chrono::milliseconds(SLICE_MS)))) {
        return false;
      }
      while (auto frame = parser_.next()) {
        if (frame->is_error) {
          continue;
        }
        if (frame->cmd == msp::MSP_FC_VARIANT) {
          variant = decode_fc_variant(frame->payload);
        } else if (frame->cmd == msp::MSP_FC_VERSION) {
          version = decode_fc_version(frame->payload);
        }
      }
    }
  }
  if (!variant || !version) {
    log_(Level::WARN, "Connected, but the FC did not say what it is: reconnecting");
    return false;
  }
  const std::string v = std::to_string(version->version_major) + "." +
    std::to_string(version->version_minor) + "." + std::to_string(version->version_patch);
  std::lock_guard<std::mutex> lock(mutex_);
  state_.version = version;
  if (variant->name != "INAV") {
    state_.wrong_firmware = true;
    log_(Level::ERROR, "The flight controller runs '" + variant->name + "', not INAV: "
      "not polling it");
    return false;
  }
  if (version->version_major != 9 || version->version_minor != 1) {
    log_(Level::WARN, "INAV " + v + ": the decoders were checked against 9.1 only");
  } else {
    log_(Level::INFO, "Connected to INAV " + v);
  }
  return true;
}

InavLink::Cycle InavLink::cycle(uint64_t n)
{
  drop_stale();
  std::vector<uint16_t> pending = {msp::MSP2_INAV_STATUS, msp::MSP2_INAV_FULL_LOCAL_POSE,
    msp::MSP2_INAV_OPTICAL_FLOW, msp::MSP_SONAR_ALTITUDE};
  if (config_.battery_every > 0 && n % static_cast<uint64_t>(config_.battery_every) == 0) {
    pending.push_back(msp::MSP2_INAV_ANALOG);
  }
  std::vector<uint8_t> request;
  for (uint16_t cmd : pending) {
    const auto one = msp::build_request(cmd);
    request.insert(request.end(), one.begin(), one.end());
  }
  if (!send_all(request)) {
    return Cycle::CLOSED;
  }
  const std::size_t asked = pending.size();
  {
    std::lock_guard<std::mutex> lock(mutex_);
    state_.requests += asked;
  }

  const auto deadline = Clock::now() + seconds(config_.reply_timeout_s);
  while (!pending.empty() && Clock::now() < deadline && !stopping_) {
    if (!read_until(std::min(deadline, Clock::now() + std::chrono::milliseconds(SLICE_MS)))) {
      return Cycle::CLOSED;
    }
    take_frames(pending);
  }
  // A damaged header can hold back replies that did arrive: give up on it.
  while (!pending.empty() && parser_.buffered() > 0) {
    parser_.skip_pending();
    take_frames(pending);
  }

  std::lock_guard<std::mutex> lock(mutex_);
  state_.missed += pending.size();
  state_.bad_crc = parser_.bad_crc_count();
  return pending.size() < asked ? Cycle::REPLIED : Cycle::SILENT;
}

void InavLink::take_frames(std::vector<uint16_t> & pending)
{
  while (auto frame = parser_.next()) {
    const auto it = std::find(pending.begin(), pending.end(), frame->cmd);
    std::lock_guard<std::mutex> lock(mutex_);
    if (it == pending.end()) {
      // A reply from an earlier cycle, or to another client on the bridge:
      // esp-link sends every byte from the FC to every connected client.
      ++state_.late;
      continue;
    }
    pending.erase(it);
    state_.last_reply = Clock::now();
    if (frame->is_error) {
      ++state_.error_frames;
      continue;
    }
    ++state_.replies;
    store(*frame);
  }
}

void InavLink::store(const msp::Frame & frame)
{
  // Called with mutex_ held.
  const auto now = Clock::now();
  auto put = [now](auto & latest, auto decoded) {
      if (decoded) {
        latest.value = decoded;
        latest.stamp = now;
        ++latest.count;
      }
    };
  switch (frame.cmd) {
    case msp::MSP2_INAV_STATUS: put(state_.status, decode_status(frame.payload)); break;
    case msp::MSP2_INAV_FULL_LOCAL_POSE: put(state_.pose, decode_local_pose(frame.payload)); break;
    case msp::MSP2_INAV_OPTICAL_FLOW: put(state_.flow, decode_optical_flow(frame.payload)); break;
    case msp::MSP_SONAR_ALTITUDE: put(state_.range, decode_rangefinder(frame.payload)); break;
    case msp::MSP2_INAV_ANALOG: put(state_.analog, decode_analog(frame.payload)); break;
    default: break;
  }
}

void InavLink::drop_stale()
{
  // Whatever arrived since the last cycle ended answers an older request.
  read_until(Clock::now());
  std::vector<uint16_t> none;
  take_frames(none);
}

bool InavLink::send_all(const std::vector<uint8_t> & bytes)
{
  std::size_t sent = 0;
  const auto deadline = Clock::now() + seconds(config_.reply_timeout_s);
  while (sent < bytes.size()) {
    const ssize_t n = ::send(fd_, bytes.data() + sent, bytes.size() - sent, MSG_NOSIGNAL);
    if (n > 0) {
      sent += static_cast<std::size_t>(n);
      continue;
    }
    if (n < 0 && (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR) &&
      Clock::now() < deadline && !stopping_)
    {
      pollfd p{fd_, POLLOUT, 0};
      poll(&p, 1, ms_until(deadline));
      continue;
    }
    return false;
  }
  return true;
}

bool InavLink::read_until(Clock::time_point until)
{
  uint8_t buf[512];
  do {
    pollfd p{fd_, POLLIN, 0};
    const int ready = poll(&p, 1, ms_until(until));
    if (ready <= 0) {
      continue;   // nothing yet (or EINTR): check the time again
    }
    const ssize_t n = ::recv(fd_, buf, sizeof(buf), 0);
    if (n == 0) {
      return false;   // closed by the bridge
    }
    if (n < 0) {
      if (errno == EAGAIN || errno == EWOULDBLOCK || errno == EINTR) {
        continue;
      }
      return false;
    }
    parser_.feed(buf, static_cast<std::size_t>(n));
  } while (Clock::now() < until && !stopping_);
  return true;
}

bool InavLink::sleep_for(double s)
{
  const auto until = Clock::now() + seconds(s);
  while (!stopping_ && Clock::now() < until) {
    std::this_thread::sleep_for(std::chrono::milliseconds(std::min(SLICE_MS, ms_until(until) + 1)));
  }
  return !stopping_;
}
}  // namespace inav
