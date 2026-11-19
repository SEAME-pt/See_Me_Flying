// Polls the FC and keeps a Telemetry struct up to date.
#pragma once

#include <functional>
#include <optional>
#include <vector>

#include "msp/client.hpp"
#include "msp/telemetry.hpp"

namespace msp {

class Poller {
public:
    Poller(Client& client, Telemetry& telemetry, int timeout_ms);

    // Reads version, board, craft name and mode names once.
    // Returns false if the FC answered none of them.
    bool read_static();

    // One pass over every live message. after_each() runs after each reply
    // (e.g. to redraw); returning false from it stops the pass early.
    void poll_cycle(const std::function<bool()>& after_each);

private:
    struct Entry {
        uint16_t cmd;
        std::function<void(Telemetry&, const Payload&)> on_ok;
        std::function<void(Telemetry&)> on_timeout;
        std::function<void(Telemetry&)> on_unsupported;
        bool enabled = true;
    };

    template <class T>
    static Entry entry(uint16_t cmd, Slot<T> Telemetry::*slot, T (*decode)(const Payload&));

    Client& client_;
    Telemetry& t_;
    int timeout_ms_;
    std::vector<Entry> entries_;
    std::optional<Clock::time_point> last_cycle_start_;
};

}  // namespace msp
