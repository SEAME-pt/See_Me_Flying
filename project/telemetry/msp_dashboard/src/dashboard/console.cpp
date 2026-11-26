#include "console.hpp"

#include <algorithm>
#include <cctype>
#include <optional>
#include <sstream>
#include <vector>

namespace dash {

namespace {

using Result = msp::CommandRecord::Result;

std::vector<std::string> split(const std::string& line) {
    std::istringstream in(line);
    std::vector<std::string> words;
    for (std::string w; in >> w;) words.push_back(w);
    return words;
}

std::optional<long> parse_int(const std::string& s) {
    if (s.empty() || s.size() > 6) return std::nullopt;
    if (!std::all_of(s.begin(), s.end(), [](unsigned char c) { return std::isdigit(c); }))
        return std::nullopt;
    return std::stol(s);
}

// "1150" -> 1150, "15%" -> 1150 (percent of the 1000-2000 range).
std::optional<uint16_t> parse_motor_value(const std::string& s) {
    if (!s.empty() && s.back() == '%') {
        const auto pct = parse_int(s.substr(0, s.size() - 1));
        if (!pct || *pct > 100) return std::nullopt;
        return static_cast<uint16_t>(1000 + *pct * 10);
    }
    const auto v = parse_int(s);
    if (!v || *v < 1000 || *v > 2000) return std::nullopt;
    return static_cast<uint16_t>(*v);
}

std::optional<bool> fc_armed(const msp::Telemetry& t) {
    if (!t.status.value || t.status.state != msp::SlotState::Fresh) return std::nullopt;
    return t.status.value->armed();
}

}  // namespace

void run_command(const std::string& line, const msp::Telemetry& t,
                 msp::Commander& commander, msp::MotorTest& motors) {
    auto words = split(line);
    if (words.empty()) return;
    std::string verb = words[0];
    std::transform(verb.begin(), verb.end(), verb.begin(), [](unsigned char c) { return std::tolower(c); });

    const std::string bad_value = "value must be 1000-2000 or 0-100%";

    if (verb == "help" || verb == "?") {
        commander.note(line, Result::Info,
                       "motor <n> <1000-2000|pct%>  ·  motors <value>  ·  stop  ·  space = STOP  ·  Esc = cancel");
    } else if (verb == "motor" || verb == "m") {
        if (words.size() != 3) return void(commander.note(line, Result::Invalid, "usage: motor <n> <value>"));
        const auto n = parse_int(words[1]);
        const auto v = parse_motor_value(words[2]);
        if (!n || *n < 1) return void(commander.note(line, Result::Invalid, "motor number must be 1 or more"));
        if (!v) return void(commander.note(line, Result::Invalid, bad_value));
        motors.set(static_cast<int>(*n), *v, fc_armed(t), line);
    } else if (verb == "motors" || verb == "all") {
        if (words.size() != 2) return void(commander.note(line, Result::Invalid, "usage: motors <value>"));
        const auto v = parse_motor_value(words[1]);
        if (!v) return void(commander.note(line, Result::Invalid, bad_value));
        motors.set(0, *v, fc_armed(t), line);
    } else if (verb == "stop" || verb == "s") {
        motors.stop(line);
    } else {
        commander.note(line, Result::Invalid, "unknown command - type help");
    }
}

}  // namespace dash
