// Bottom panel: the log of commands sent and the command input line.
#pragma once

#include <deque>
#include <string>

#include "msp/commander.hpp"

namespace dash {

struct InputLine {
    bool editing = false;
    std::string text;
};

class CommandPanel {
public:
    // Rows the panel needs for a terminal of this height.
    static int height_for(int rows);

    // Draws the static parts; the panel occupies rows [top, top + height).
    std::string layout(int cols, int top, int height);
    // Rewrites the log if a record was added, and the input line if it changed.
    std::string update(const std::deque<msp::CommandRecord>& history, unsigned long revision,
                       const InputLine& input);

private:
    int cols_ = 0, top_ = 0, log_lines_ = 0;
    unsigned long shown_revision_ = ~0UL;
    std::string shown_input_;
};

}  // namespace dash
