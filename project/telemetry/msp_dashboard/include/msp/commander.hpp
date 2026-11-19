// Sending commands to the FC, with a log of everything sent.
// Lives in msp_core so the ROS bridge can reuse it.
#pragma once

#include <array>
#include <chrono>
#include <cstdint>
#include <deque>
#include <fstream>
#include <optional>
#include <string>

#include "msp/client.hpp"

namespace msp {

struct CommandRecord {
    enum class Result {
        Ack,          // FC accepted it
        Rejected,     // FC answered with an MSP error
        NoReply,      // no answer in time (it may or may not have been applied)
        Blocked,      // refused locally by a safety check, nothing sent
        Invalid,      // could not be parsed / bad arguments, nothing sent
        Info,         // a note, e.g. help text
    };
    std::chrono::system_clock::time_point when;
    std::string text;       // what the user typed (or why it was sent)
    uint16_t cmd = 0;       // MSP command id, 0 if nothing was sent
    std::string cmd_name;
    Result result = Result::Info;
    int latency_ms = 0;
    std::string detail;
};

const char* result_name(CommandRecord::Result r);

class Commander {
public:
    Commander(Client& client, int timeout_ms, size_t keep = 200);

    // Sends a command, waits for the ack, and logs the outcome.
    const CommandRecord& send(const std::string& text, uint16_t cmd, const std::string& cmd_name,
                              const Payload& payload);
    // Logs something that was not sent (blocked, invalid, info).
    const CommandRecord& note(const std::string& text, CommandRecord::Result result,
                              const std::string& detail);

    const std::deque<CommandRecord>& history() const { return history_; }
    unsigned long revision() const { return revision_; }  // bumps on every new record

    // Also append every record to a text file.
    bool open_log_file(const std::string& path);

private:
    const CommandRecord& push(CommandRecord r);

    Client& client_;
    int timeout_ms_;
    size_t keep_;
    std::deque<CommandRecord> history_;
    unsigned long revision_ = 0;
    std::ofstream file_;
};

// Motor test through MSP_SET_MOTOR, with safety limits:
//  - off unless enabled explicitly
//  - refused while the FC reports armed (INAV ignores it then anyway)
//  - values above max_value are refused, below stop_value are raised to it
//  - motors are stopped automatically after auto_stop_s without a new command
struct MotorLimits {
    bool enabled = false;
    uint16_t stop_value = 1000;
    uint16_t max_value = 1500;
    int auto_stop_s = 15;     // 0 = never
    int motor_count = 4;
};

class MotorTest {
public:
    MotorTest(Commander& commander, MotorLimits limits);

    // motor: 1..motor_count, or 0 for all. fc_armed: nullopt if not known yet.
    void set(int motor, uint16_t value, std::optional<bool> fc_armed, const std::string& text);
    void stop(const std::string& text);
    void tick();   // call regularly: handles the auto-stop

    bool spinning() const;
    bool used() const { return used_; }
    const std::array<uint16_t, 8>& setpoints() const { return setpoints_; }
    const MotorLimits& limits() const { return limits_; }
    std::optional<int> seconds_to_auto_stop() const;

private:
    void send(const std::array<uint16_t, 8>& values, const std::string& text);

    Commander& commander_;
    MotorLimits limits_;
    std::array<uint16_t, 8> setpoints_;
    bool used_ = false;
    std::chrono::steady_clock::time_point last_change_{};
};

}  // namespace msp
