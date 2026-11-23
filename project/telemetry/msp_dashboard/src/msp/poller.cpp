#include "msp/poller.hpp"

#include <algorithm>

namespace msp {

template <class T>
Poller::Entry Poller::entry(uint16_t cmd, Slot<T> Telemetry::*slot, T (*decode)(const Payload&)) {
    Entry e;
    e.cmd = cmd;
    e.on_ok = [slot, decode](Telemetry& t, const Payload& p) {
        try {
            (t.*slot).set(decode(p));
        } catch (const DecodeError&) {
            (t.*slot).undecodable(p);
        }
    };
    e.on_timeout = [slot](Telemetry& t) { (t.*slot).timed_out(); };
    e.on_unsupported = [slot](Telemetry& t) { (t.*slot).unsupported(); };
    return e;
}

Poller::Poller(Client& client, Telemetry& telemetry, int timeout_ms)
    : client_(client), t_(telemetry), timeout_ms_(timeout_ms) {
    // Same live set as inav_telemetry.py. Comment a line out to stop polling it.
    entries_ = {
        entry(cmd::ATTITUDE, &Telemetry::attitude, decode_attitude),
        entry(cmd::ALTITUDE, &Telemetry::altitude, decode_altitude),
        entry(cmd::RAW_IMU, &Telemetry::imu, decode_raw_imu),
        entry(cmd::RC, &Telemetry::rc, decode_u16_list),
        entry(cmd::MOTOR, &Telemetry::motors, decode_u16_list),
        entry(cmd::INAV_STATUS, &Telemetry::status, decode_inav_status),
        entry(cmd::INAV_ANALOG, &Telemetry::analog, decode_inav_analog),
        entry(cmd::INAV_OPTICAL_FLOW, &Telemetry::opflow, decode_optical_flow),
        entry(cmd::SONAR_ALTITUDE, &Telemetry::rangefinder, decode_rangefinder),
        entry(cmd::INAV_FULL_LOCAL_POSE, &Telemetry::pose, decode_local_pose),
        entry(cmd::NAV_STATUS, &Telemetry::nav, decode_nav_status),
        entry(cmd::INAV_LINK_STATS, &Telemetry::link_stats, decode_link_stats),
    };
}

bool Poller::read_static() {
    bool answered = false;
    auto ask = [&](uint16_t cmd, int timeout_ms) -> std::optional<Payload> {
        Reply r = client_.request(cmd, {}, timeout_ms);
        if (r.status != Reply::Status::Timeout) answered = true;
        if (r.status == Reply::Status::Ok) return std::move(r.payload);
        return std::nullopt;
    };
    auto safely = [](auto&& fn) {
        try {
            fn();
        } catch (const DecodeError&) {
        }
    };

    if (auto p = ask(cmd::API_VERSION, timeout_ms_)) safely([&] { t_.info.api = decode_api_version(*p); });
    if (auto p = ask(cmd::FC_VARIANT, timeout_ms_)) t_.info.variant = decode_text(*p);
    if (auto p = ask(cmd::FC_VERSION, timeout_ms_)) safely([&] { t_.info.version = decode_fc_version(*p); });
    if (auto p = ask(cmd::BOARD_INFO, timeout_ms_)) safely([&] { t_.info.board = decode_board_info(*p); });
    if (auto p = ask(cmd::NAME, timeout_ms_)) t_.info.craft_name = decode_text(*p);
    // MSP_BOXNAMES is a long reply: give it more time and retry if it gets lost.
    for (int attempt = 0; attempt < 3 && t_.info.box_names.empty(); ++attempt)
        if (auto p = ask(cmd::BOXNAMES, timeout_ms_ * 2)) t_.info.box_names = decode_box_names(*p);

    return answered;
}

void Poller::poll_cycle(const std::function<bool()>& after_each) {
    const auto start = Clock::now();
    if (last_cycle_start_) {
        const double dt = std::chrono::duration<double>(start - *last_cycle_start_).count();
        if (dt > 0) {
            const double hz = 1.0 / dt;
            t_.cycle_hz = t_.cycle_hz == 0 ? hz : 0.8 * t_.cycle_hz + 0.2 * hz;  // smoothed
        }
    }
    last_cycle_start_ = start;

    bool any_answer = false;
    LinkTiming timing;
    double total_ms = 0;
    for (Entry& e : entries_) {
        if (!e.enabled) continue;
        const auto sent = Clock::now();
        Reply r = client_.request(e.cmd, {}, timeout_ms_);
        const double rtt_ms = std::chrono::duration<double, std::milli>(Clock::now() - sent).count();
        if (r.status == Reply::Status::Timeout) {
            ++timing.timeouts;
        } else {
            timing.min_ms = timing.samples == 0 ? rtt_ms : std::min(timing.min_ms, rtt_ms);
            timing.max_ms = std::max(timing.max_ms, rtt_ms);
            total_ms += rtt_ms;
            ++timing.samples;
        }
        switch (r.status) {
            case Reply::Status::Ok:
                any_answer = true;
                e.on_ok(t_, r.payload);
                break;
            case Reply::Status::Error:  // FC doesn't support it: stop asking
                any_answer = true;
                e.enabled = false;
                e.on_unsupported(t_);
                break;
            case Reply::Status::Timeout:
                e.on_timeout(t_);
                break;
        }
        if (!after_each()) return;
    }
    timing.cycle_ms = std::chrono::duration<double, std::milli>(Clock::now() - start).count();
    if (timing.samples > 0) {
        timing.avg_ms = total_ms / timing.samples;
        const double prev = t_.timing.smoothed_ms;
        timing.smoothed_ms = prev == 0 ? timing.avg_ms : 0.7 * prev + 0.3 * timing.avg_ms;
    } else {
        timing.smoothed_ms = t_.timing.smoothed_ms;
    }
    t_.timing = timing;
    t_.fc_responding = any_answer;
    ++t_.cycles;
}

}  // namespace msp
