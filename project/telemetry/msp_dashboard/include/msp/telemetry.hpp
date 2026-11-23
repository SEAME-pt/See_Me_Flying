// Latest known state of the flight controller. The dashboard reads it now;
// a ROS node can publish from the same struct later.
#pragma once

#include <chrono>
#include <optional>
#include <string>
#include <vector>

#include "msp/messages.hpp"

namespace msp {

using Clock = std::chrono::steady_clock;

enum class SlotState {
    Waiting,       // not polled yet
    NoReply,       // polled, never answered
    Fresh,         // last poll succeeded
    Stale,         // has a value, but the last poll timed out
    Unsupported,   // FC answered with an MSP error; no longer polled
    Undecodable,   // reply too short / wrong layout; raw bytes kept
};

template <class T>
struct Slot {
    std::optional<T> value;
    Payload raw;
    SlotState state = SlotState::Waiting;
    Clock::time_point updated{};

    void set(T v) {
        value = std::move(v);
        raw.clear();
        state = SlotState::Fresh;
        updated = Clock::now();
    }
    void timed_out() { state = value ? SlotState::Stale : SlotState::NoReply; }
    void unsupported() { value.reset(); state = SlotState::Unsupported; }
    void undecodable(const Payload& p) { value.reset(); raw = p; state = SlotState::Undecodable; }
};

struct FcInfo {
    std::optional<ApiVersion> api;
    std::string variant, version, craft_name;
    std::optional<BoardInfo> board;
    std::vector<std::string> box_names;
};

// Round-trip times of the requests in the last complete polling cycle:
// from writing a request to receiving its reply. Measured from timestamps the
// poller takes anyway, so it costs no extra MSP traffic.
struct LinkTiming {
    int samples = 0;           // replies in the last cycle
    int timeouts = 0;          // requests without a reply in the last cycle
    double min_ms = 0, avg_ms = 0, max_ms = 0;
    double smoothed_ms = 0;    // average over the last few cycles (steadier to read)
    double cycle_ms = 0;       // time to poll every message once
};

struct Telemetry {
    FcInfo info;
    std::string link;            // "192.168.4.1:23" or "/dev/ttyUSB0 @ 115200"

    Slot<Attitude> attitude;
    Slot<Altitude> altitude;
    Slot<RawImu> imu;
    Slot<std::vector<uint16_t>> rc;
    Slot<std::vector<uint16_t>> motors;
    Slot<InavStatus> status;
    Slot<InavAnalog> analog;
    Slot<OpticalFlow> opflow;
    Slot<Rangefinder> rangefinder;
    Slot<LocalPose> pose;
    Slot<NavStatus> nav;
    Slot<LinkStats> link_stats;

    bool fc_responding = true;
    double cycle_hz = 0;         // measured polling rate
    LinkTiming timing;
    unsigned long cycles = 0;
};

}  // namespace msp
