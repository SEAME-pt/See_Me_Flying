#include "msp/commander.hpp"

#include <algorithm>
#include <ctime>

#include "msp/messages.hpp"

namespace msp {

const char* result_name(CommandRecord::Result r) {
    switch (r) {
        case CommandRecord::Result::Ack: return "ack";
        case CommandRecord::Result::Rejected: return "REJECTED";
        case CommandRecord::Result::NoReply: return "no reply";
        case CommandRecord::Result::Blocked: return "blocked";
        case CommandRecord::Result::Invalid: return "invalid";
        case CommandRecord::Result::Info: return "info";
    }
    return "?";
}

// ---------- Commander ----------

Commander::Commander(Client& client, int timeout_ms, size_t keep)
    : client_(client), timeout_ms_(timeout_ms), keep_(keep) {}

bool Commander::open_log_file(const std::string& path) {
    file_.open(path, std::ios::app);
    return file_.is_open();
}

const CommandRecord& Commander::send(const std::string& text, uint16_t cmd,
                                     const std::string& cmd_name, const Payload& payload) {
    CommandRecord r;
    r.when = std::chrono::system_clock::now();
    r.text = text;
    r.cmd = cmd;
    r.cmd_name = cmd_name;
    const auto t0 = std::chrono::steady_clock::now();
    const Reply reply = client_.request(cmd, payload, timeout_ms_);
    r.latency_ms = static_cast<int>(std::chrono::duration_cast<std::chrono::milliseconds>(
                                        std::chrono::steady_clock::now() - t0).count());
    switch (reply.status) {
        case Reply::Status::Ok: r.result = CommandRecord::Result::Ack; break;
        case Reply::Status::Error: r.result = CommandRecord::Result::Rejected; break;
        case Reply::Status::Timeout: r.result = CommandRecord::Result::NoReply; break;
    }
    return push(std::move(r));
}

const CommandRecord& Commander::note(const std::string& text, CommandRecord::Result result,
                                     const std::string& detail) {
    CommandRecord r;
    r.when = std::chrono::system_clock::now();
    r.text = text;
    r.result = result;
    r.detail = detail;
    return push(std::move(r));
}

const CommandRecord& Commander::push(CommandRecord r) {
    if (file_.is_open()) {
        const std::time_t tt = std::chrono::system_clock::to_time_t(r.when);
        const auto ms = std::chrono::duration_cast<std::chrono::milliseconds>(
                            r.when.time_since_epoch()).count() % 1000;
        char stamp[32];
        std::strftime(stamp, sizeof stamp, "%Y-%m-%d %H:%M:%S", std::localtime(&tt));
        file_ << stamp << '.' << (ms < 100 ? (ms < 10 ? "00" : "0") : "") << ms << "  " << r.text;
        if (r.cmd) file_ << "  [" << r.cmd_name << " " << r.cmd << "]";
        file_ << "  " << result_name(r.result);
        if (r.cmd) file_ << " " << r.latency_ms << " ms";
        if (!r.detail.empty()) file_ << "  " << r.detail;
        file_ << std::endl;   // flush: the log must survive a crash
    }
    history_.push_back(std::move(r));
    while (history_.size() > keep_) history_.pop_front();
    ++revision_;
    return history_.back();
}

// ---------- MotorTest ----------

MotorTest::MotorTest(Commander& commander, MotorLimits limits)
    : commander_(commander), limits_(limits) {
    setpoints_.fill(limits_.stop_value);
}

bool MotorTest::spinning() const {
    for (int i = 0; i < limits_.motor_count; ++i)
        if (setpoints_[static_cast<size_t>(i)] > limits_.stop_value) return true;
    return false;
}

std::optional<int> MotorTest::seconds_to_auto_stop() const {
    if (!spinning() || limits_.auto_stop_s <= 0) return std::nullopt;
    const auto elapsed = std::chrono::duration_cast<std::chrono::seconds>(
                             std::chrono::steady_clock::now() - last_change_).count();
    return std::max<int>(0, limits_.auto_stop_s - static_cast<int>(elapsed));
}

void MotorTest::set(int motor, uint16_t value, std::optional<bool> fc_armed, const std::string& text) {
    using R = CommandRecord::Result;
    if (!limits_.enabled) {
        commander_.note(text, R::Blocked, "motor commands are off - restart with --enable-motors (props off!)");
        return;
    }
    if (!fc_armed) {
        commander_.note(text, R::Blocked, "arming state not known yet - wait for the status to show");
        return;
    }
    if (*fc_armed) {
        commander_.note(text, R::Blocked, "FC is ARMED - motor test only works disarmed");
        return;
    }
    if (motor < 0 || motor > limits_.motor_count) {
        commander_.note(text, R::Invalid, "motor must be 1-" + std::to_string(limits_.motor_count));
        return;
    }
    if (value > limits_.max_value) {
        commander_.note(text, R::Blocked, "above the limit " + std::to_string(limits_.max_value) +
                                              " (--motor-max)");
        return;
    }
    if (value < limits_.stop_value) value = limits_.stop_value;

    auto next = setpoints_;
    for (int i = 0; i < limits_.motor_count; ++i)
        if (motor == 0 || motor == i + 1) next[static_cast<size_t>(i)] = value;
    send(next, text);
}

void MotorTest::stop(const std::string& text) {
    if (!limits_.enabled) {
        commander_.note(text, CommandRecord::Result::Info, "motor commands are off - nothing to stop");
        return;
    }
    std::array<uint16_t, 8> next;
    next.fill(limits_.stop_value);
    send(next, text);   // always sent, even if we think they're stopped
}

void MotorTest::tick() {
    if (const auto left = seconds_to_auto_stop(); left && *left == 0)
        stop("auto-stop after " + std::to_string(limits_.auto_stop_s) + " s");
}

void MotorTest::send(const std::array<uint16_t, 8>& values, const std::string& text) {
    const CommandRecord& r = commander_.send(text, cmd::SET_MOTOR, "MSP_SET_MOTOR", encode_set_motor(values));
    // On no-reply the FC may still have applied it: assume it did, so the
    // stop / auto-stop logic still treats the motors as spinning.
    if (r.result != CommandRecord::Result::Rejected) {
        setpoints_ = values;
        used_ = true;
        last_change_ = std::chrono::steady_clock::now();
    }
}

}  // namespace msp
