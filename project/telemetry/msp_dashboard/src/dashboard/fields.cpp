#include "fields.hpp"

#include <algorithm>
#include <cstdarg>
#include <cstdio>

namespace dash {

using msp::SlotState;
using msp::Telemetry;

namespace {

std::string fmt(const char* format, ...) __attribute__((format(printf, 1, 2)));
std::string fmt(const char* format, ...) {
    char buf[256];
    va_list args;
    va_start(args, format);
    std::vsnprintf(buf, sizeof buf, format, args);
    va_end(args);
    return buf;
}

std::string join(const std::vector<std::string>& items, const char* sep = ", ") {
    std::string out;
    for (size_t i = 0; i < items.size(); ++i) out += (i ? sep : "") + items[i];
    return out;
}

// Builds a getter for a value that comes from one MSP message. Handles the
// "no data yet / no reply / unsupported / stale" cases the same way everywhere;
// `show` only has to translate a real value.
template <class T, class F>
Getter from(msp::Slot<T> Telemetry::*slot, F show) {
    return [slot, show](const Telemetry& t) -> Cell {
        const msp::Slot<T>& s = t.*slot;
        switch (s.state) {
            case SlotState::Waiting: return {"…", style::kDim};
            case SlotState::NoReply: return {"no reply", style::kWarn};
            case SlotState::Unsupported: return {"not supported by FC", style::kDim};
            case SlotState::Undecodable:
                return {fmt("unexpected payload (%zu bytes)", s.raw.size()), style::kBad};
            case SlotState::Fresh:
            case SlotState::Stale: break;
        }
        Cell c = show(*s.value, t);
        if (s.state == SlotState::Stale) c.style = style::kDim;  // last known value
        return c;
    };
}

Cell value(std::string text, const char* st = style::kValue) { return {std::move(text), st}; }

// ---------- RC / motors ----------

constexpr const char* kStickNames[] = {"Roll", "Pitch", "Throttle", "Yaw"};  // INAV default AETR map

Field rc_stick(size_t i) {
    return {std::string(kStickNames[i]) + fmt(" (ch%zu)", i + 1),
            from(&Telemetry::rc, [i](const std::vector<uint16_t>& ch, const Telemetry&) {
                if (i >= ch.size()) return value("-", style::kDim);
                if (i == 2) return value(fmt("%4u  %3.0f %%", ch[i], std::clamp((ch[i] - 1000) / 10.0, 0.0, 100.0)));
                return value(fmt("%4u  %+4d", ch[i], ch[i] - 1500));
            })};
}

Field rc_aux_group(size_t first) {
    const size_t aux = first - 3;  // channel 5 = AUX1
    return {fmt("AUX %zu-%zu", aux, aux + 3),
            from(&Telemetry::rc, [first](const std::vector<uint16_t>& ch, const Telemetry&) {
                if (first >= ch.size()) return value("-", style::kDim);
                std::string s;
                for (size_t i = first; i < first + 4 && i < ch.size(); ++i) s += fmt("%5u", ch[i]);
                return value(s);
            })};
}

Field motor(size_t i) {
    return {fmt("Motor %zu", i + 1),
            from(&Telemetry::motors, [i](const std::vector<uint16_t>& m, const Telemetry&) {
                if (i >= m.size()) return value("-", style::kDim);
                const double pct = std::clamp((m[i] - 1000) / 10.0, 0.0, 100.0);
                return value(fmt("%4u  %3.0f %%", m[i], pct), m[i] > 1000 ? style::kWarn : style::kValue);
            })};
}

}  // namespace

// ---------- header ----------

std::vector<Field> header_fields(const msp::MotorTest& motors) {
    return {
        {"Flight controller",
         [](const Telemetry& t) {
             const auto& i = t.info;
             std::vector<std::string> parts;
             if (!i.variant.empty() || !i.version.empty()) parts.push_back(i.variant + " " + i.version);
             if (i.board) parts.push_back(i.board->target.empty() ? i.board->board_id : i.board->target);
             if (i.api) parts.push_back(fmt("MSP API %d.%d", i.api->major, i.api->minor));
             if (!i.craft_name.empty()) parts.push_back("craft \"" + i.craft_name + "\"");
             return parts.empty() ? value("unknown", style::kDim) : value(join(parts, "  ·  "));
         }},
        {"Connection",
         [](const Telemetry& t) {
             if (t.cycles == 0) return value(t.link + "  ·  connecting…", style::kDim);
             if (!t.fc_responding) return value(t.link + "  ·  FC NOT RESPONDING", style::kBad);
             return value(fmt("%s  ·  FC responding  ·  %.1f Hz", t.link.c_str(), t.cycle_hz), style::kGood);
         }},
        {"Latency",
         [](const Telemetry& t) {
             const auto& lt = t.timing;
             if (t.cycles == 0) return value("…", style::kDim);
             if (lt.samples == 0) return value("no replies in the last cycle", style::kBad);
             std::string txt = fmt("%.1f ms  ·  min %.1f  ·  max %.1f  ·  full cycle %.0f ms",
                                   lt.smoothed_ms, lt.min_ms, lt.max_ms, lt.cycle_ms);
             if (lt.timeouts) txt += fmt("  ·  %d timed out", lt.timeouts);
             const char* st = lt.timeouts || lt.smoothed_ms > 150 ? style::kBad
                            : lt.smoothed_ms > 50                 ? style::kWarn
                                                                  : style::kGood;
             return value(txt, st);
         }},
        {"Armed",
         from(&Telemetry::status, [](const msp::InavStatus& s, const Telemetry&) {
             return s.armed() ? value("ARMED", style::kBad) : value("disarmed", style::kGood);
         })},
        {"Flight modes",
         from(&Telemetry::status, [](const msp::InavStatus& s, const Telemetry& t) {
             auto modes = msp::active_modes(s.mode_mask, t.info.box_names);
             // ARM is already shown above.
             modes.erase(std::remove(modes.begin(), modes.end(), "ARM"), modes.end());
             return modes.empty() ? value("none (acro)") : value(join(modes));
         })},
        {"Arming blockers",
         from(&Telemetry::status, [](const msp::InavStatus& s, const Telemetry&) {
             const auto blockers = msp::arming_blockers(s.arming_flags);
             if (blockers.empty()) return value(s.armed() ? "none" : "none - ready to arm", style::kGood);
             return value(join(blockers), style::kWarn);
         })},
        {"Motor test",
         [&motors](const Telemetry&) {
             const auto& lim = motors.limits();
             if (!lim.enabled) return value("off  (start with --enable-motors to send motor commands)", style::kDim);
             if (!motors.spinning())
                 return value(fmt("ready  ·  stopped  ·  limit %u  ·  auto-stop %d s",
                                  lim.max_value, lim.auto_stop_s), style::kGood);
             std::string txt = "SPINNING ";
             for (int i = 0; i < lim.motor_count; ++i) txt += fmt(" %u", motors.setpoints()[static_cast<size_t>(i)]);
             if (const auto left = motors.seconds_to_auto_stop()) txt += fmt("  ·  auto-stop in %d s", *left);
             return value(txt + "  ·  space = STOP", style::kBad);
         }},
    };
}

// ---------- sections ----------

std::vector<Section> sections() {
    using namespace msp;
    std::vector<Section> out;

    out.push_back({"Attitude", {
        {"Roll", from(&Telemetry::attitude, [](const Attitude& a, const Telemetry&) { return value(fmt("%+7.1f °", a.roll_deg)); })},
        {"Pitch", from(&Telemetry::attitude, [](const Attitude& a, const Telemetry&) { return value(fmt("%+7.1f °", a.pitch_deg)); })},
        {"Heading", from(&Telemetry::attitude, [](const Attitude& a, const Telemetry&) { return value(fmt("%5.0f °", a.heading_deg)); })},
    }});

    out.push_back({"Position (INAV estimate)", {
        {"X", from(&Telemetry::pose, [](const LocalPose& p, const Telemetry&) { return value(fmt("%+8.2f m", p.pos_m[0])); })},
        {"Y", from(&Telemetry::pose, [](const LocalPose& p, const Telemetry&) { return value(fmt("%+8.2f m", p.pos_m[1])); })},
        {"Z", from(&Telemetry::pose, [](const LocalPose& p, const Telemetry&) { return value(fmt("%+8.2f m", p.pos_m[2])); })},
        {"Velocity X", from(&Telemetry::pose, [](const LocalPose& p, const Telemetry&) { return value(fmt("%+8.2f m/s", p.vel_ms[0])); })},
        {"Velocity Y", from(&Telemetry::pose, [](const LocalPose& p, const Telemetry&) { return value(fmt("%+8.2f m/s", p.vel_ms[1])); })},
        {"Velocity Z", from(&Telemetry::pose, [](const LocalPose& p, const Telemetry&) { return value(fmt("%+8.2f m/s", p.vel_ms[2])); })},
        {"Yaw", from(&Telemetry::pose, [](const LocalPose& p, const Telemetry&) { return value(fmt("%+7.1f °", p.yaw_deg)); })},
    }});

    out.push_back({"Altitude", {
        {"Altitude (est.)", from(&Telemetry::altitude, [](const Altitude& a, const Telemetry&) { return value(fmt("%+8.2f m", a.alt_m)); })},
        {"Vertical speed", from(&Telemetry::altitude, [](const Altitude& a, const Telemetry&) { return value(fmt("%+8.2f m/s", a.vario_ms)); })},
        {"Rangefinder", from(&Telemetry::rangefinder, [](const Rangefinder& r, const Telemetry&) {
             if (r.valid()) return value(fmt("%8.2f m", r.distance_m()));
             if (r.raw_cm == 0) return value("no rangefinder running", style::kWarn);
             if (r.raw_cm == -1) return value("out of range", style::kWarn);
             return value(fmt("no reading (%d)", r.raw_cm), style::kWarn);
         })},
    }});

    out.push_back({"Optical flow", {
        {"Surface quality", from(&Telemetry::opflow, [](const OpticalFlow& f, const Telemetry&) {
             return value(fmt("%3d / 255  (%3.0f %%)", f.quality, f.quality / 2.55));
         })},
        {"Flow rate X", from(&Telemetry::opflow, [](const OpticalFlow& f, const Telemetry&) { return value(fmt("%+5d °/s", f.flow_x_dps)); })},
        {"Flow rate Y", from(&Telemetry::opflow, [](const OpticalFlow& f, const Telemetry&) { return value(fmt("%+5d °/s", f.flow_y_dps)); })},
        {"Body rate X", from(&Telemetry::opflow, [](const OpticalFlow& f, const Telemetry&) { return value(fmt("%+5d °/s", f.body_x_dps)); })},
        {"Body rate Y", from(&Telemetry::opflow, [](const OpticalFlow& f, const Telemetry&) { return value(fmt("%+5d °/s", f.body_y_dps)); })},
    }});

    auto battery_style = [](const InavAnalog& a) {
        switch (a.battery_state) {
            case 0: return style::kGood;
            case 1: return style::kWarn;
            case 2: return style::kBad;
            default: return style::kDim;
        }
    };
    out.push_back({"Battery", {
        {"State", from(&Telemetry::analog, [battery_style](const InavAnalog& a, const Telemetry&) {
             return value(battery_state_name(a.battery_state), battery_style(a));
         })},
        {"Voltage", from(&Telemetry::analog, [](const InavAnalog& a, const Telemetry&) { return value(fmt("%6.2f V", a.voltage_v)); })},
        {"Per cell", from(&Telemetry::analog, [](const InavAnalog& a, const Telemetry&) {
             if (a.cell_count == 0) return value("cell count unknown", style::kDim);
             return value(fmt("%6.2f V  (%dS)", a.voltage_v / a.cell_count, a.cell_count));
         })},
        {"Current", from(&Telemetry::analog, [](const InavAnalog& a, const Telemetry&) { return value(fmt("%6.2f A", a.current_a)); })},
        {"Power", from(&Telemetry::analog, [](const InavAnalog& a, const Telemetry&) { return value(fmt("%6.1f W", a.power_w)); })},
        {"Used", from(&Telemetry::analog, [](const InavAnalog& a, const Telemetry&) {
             return value(fmt("%d mAh  ·  %.2f Wh", a.mah_drawn, a.mwh_drawn / 1000.0));
         })},
        {"Charge left", from(&Telemetry::analog, [battery_style](const InavAnalog& a, const Telemetry&) {
             if (!a.uses_capacity_thresholds) return value(fmt("%3d %%", a.battery_pct), battery_style(a));
             return value(fmt("%3d %%  (%u left)", a.battery_pct, a.remaining_capacity), battery_style(a));
         })},
    }});

    out.push_back({"Radio link", {
        {"RSSI (FC)", from(&Telemetry::analog, [](const InavAnalog& a, const Telemetry&) { return value(fmt("%5.1f %%", a.rssi_pct)); })},
        {"Uplink RSSI", from(&Telemetry::link_stats, [](const LinkStats& l, const Telemetry&) { return value(fmt("%4d dBm", l.rssi_dbm)); })},
        {"Link quality", from(&Telemetry::link_stats, [](const LinkStats& l, const Telemetry&) {
             return value(fmt("%3d %%", l.link_quality_pct), l.link_quality_pct < 70 ? style::kWarn : style::kValue);
         })},
        {"SNR", from(&Telemetry::link_stats, [](const LinkStats& l, const Telemetry&) { return value(fmt("%+4d dB", l.snr_db)); })},
    }});

    out.push_back({"System", {
        {"CPU load", from(&Telemetry::status, [](const InavStatus& s, const Telemetry&) { return value(fmt("%3d %%", s.cpu_load_pct)); })},
        {"Loop time", from(&Telemetry::status, [](const InavStatus& s, const Telemetry&) {
             if (s.cycle_time_us == 0) return value("0 µs");
             return value(fmt("%d µs  (%.0f Hz)", s.cycle_time_us, 1e6 / s.cycle_time_us));
         })},
        {"I2C errors", from(&Telemetry::status, [](const InavStatus& s, const Telemetry&) {
             return value(fmt("%d", s.i2c_errors), s.i2c_errors ? style::kWarn : style::kValue);
         })},
        {"Sensors", from(&Telemetry::status, [](const InavStatus& s, const Telemetry&) {
             const auto names = sensor_names(s.sensor_bits);
             return names.empty() ? value("none", style::kWarn) : value(join(names));
         })},
        {"Hardware", from(&Telemetry::status, [](const InavStatus& s, const Telemetry&) {
             return s.hardware_ok ? value("ok", style::kGood) : value("SENSOR FAILURE", style::kBad);
         })},
        {"Profiles", from(&Telemetry::status, [](const InavStatus& s, const Telemetry&) {
             std::string txt = fmt("PID %d · batt %d", s.pid_profile, s.battery_profile);
             if (s.mixer_profile) txt += fmt(" · mix %d", *s.mixer_profile);
             return value(txt);
         })},
    }});

    out.push_back({"Navigation", {
        {"Mode", from(&Telemetry::nav, [](const NavStatus& n, const Telemetry&) { return value(nav_mode_name(n.mode)); })},
        {"State", from(&Telemetry::nav, [](const NavStatus& n, const Telemetry&) { return value(nav_state_name(n.state)); })},
        {"Waypoint", from(&Telemetry::nav, [](const NavStatus& n, const Telemetry&) {
             return value(fmt("#%d  %s", n.wp_number, wp_action_name(n.wp_action).c_str()));
         })},
        {"Error", from(&Telemetry::nav, [](const NavStatus& n, const Telemetry&) {
             return value(nav_error_name(n.error), n.error ? style::kWarn : style::kValue);
         })},
        {"Heading target", from(&Telemetry::nav, [](const NavStatus& n, const Telemetry&) { return value(fmt("%d °", n.heading_target_deg)); })},
    }});

    out.push_back({"RC channels", {
        rc_stick(0), rc_stick(1), rc_stick(2), rc_stick(3),
        rc_aux_group(4), rc_aux_group(8), rc_aux_group(12),
    }});

    out.push_back({"Motors", {motor(0), motor(1), motor(2), motor(3)}});

    out.push_back({"IMU (raw)", {
        {"Accel", from(&Telemetry::imu, [](const RawImu& i, const Telemetry&) {
             return value(fmt("%+5.2f %+5.2f %+5.2f g", i.acc_g[0], i.acc_g[1], i.acc_g[2]));
         })},
        {"Gyro", from(&Telemetry::imu, [](const RawImu& i, const Telemetry&) {
             return value(fmt("%+5.0f %+5.0f %+5.0f °/s", i.gyro_dps[0], i.gyro_dps[1], i.gyro_dps[2]));
         })},
        {"Mag", from(&Telemetry::imu, [](const RawImu& i, const Telemetry&) {
             return value(fmt("%5d %5d %5d", i.mag[0], i.mag[1], i.mag[2]));
         })},
    }});

    return out;
}

}  // namespace dash
