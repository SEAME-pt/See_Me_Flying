#include "command_panel.hpp"

#include <algorithm>
#include <ctime>
#include <utility>
#include <vector>

#include "dashboard.hpp"

namespace dash {

namespace {

using Result = msp::CommandRecord::Result;

const char* result_style(Result r) {
    switch (r) {
        case Result::Ack: return style::kGood;
        case Result::Rejected: return style::kBad;
        case Result::NoReply:
        case Result::Blocked:
        case Result::Invalid: return style::kWarn;
        case Result::Info: return style::kDim;
    }
    return style::kValue;
}

// A line made of colored pieces, padded/truncated to exactly `width` columns.
std::string render(const std::vector<std::pair<const char*, std::string>>& pieces, int width) {
    std::string out;
    int used = 0;
    for (const auto& [st, text] : pieces) {
        if (used >= width) break;
        const std::string part = display_width(text) > width - used ? fit(text, width - used) : text;
        out += std::string(style::kReset) + st + part;  // reset: dim would carry over
        used += display_width(part);
    }
    return out + style::kReset + std::string(static_cast<size_t>(std::max(0, width - used)), ' ');
}

std::string clock_text(std::chrono::system_clock::time_point t) {
    const std::time_t tt = std::chrono::system_clock::to_time_t(t);
    char buf[16];
    std::strftime(buf, sizeof buf, "%H:%M:%S", std::localtime(&tt));
    return buf;
}

std::string record_line(const msp::CommandRecord& r, int width) {
    std::string result = msp::result_name(r.result);
    if (r.cmd) result += " " + std::to_string(r.latency_ms) + " ms";
    std::string extra = r.detail;
    if (r.cmd) extra = r.cmd_name + " (" + std::to_string(r.cmd) + ")" + (extra.empty() ? "" : "  " + extra);
    return render({{style::kDim, clock_text(r.when) + "  "},
                   {style::kValue, fit(r.text, 24) + "  "},
                   {result_style(r.result), fit(result, 13) + "  "},
                   {style::kDim, extra}},
                  width);
}

}  // namespace

int CommandPanel::height_for(int rows) {
    const int log_lines = std::clamp(rows / 6, 3, 8);
    return log_lines + 2;   // title + log + input line
}

std::string CommandPanel::layout(int cols, int top, int height) {
    cols_ = cols;
    top_ = top;
    log_lines_ = std::max(1, height - 2);
    shown_revision_ = ~0UL;
    shown_input_.clear();

    std::string title = "── Commands sent ";
    while (display_width(title) < cols - 2) title += "─";
    return at(top_, 2) + style::kSection + title + style::kReset;
}

std::string CommandPanel::update(const std::deque<msp::CommandRecord>& history,
                                 unsigned long revision, const InputLine& input) {
    std::string out;
    const int width = cols_ - 2;

    if (revision != shown_revision_) {
        shown_revision_ = revision;
        // Newest record on the bottom line, older ones above it.
        const size_t n = std::min(history.size(), static_cast<size_t>(log_lines_));
        const int first_row = top_ + 1 + (log_lines_ - static_cast<int>(n));
        for (int row = top_ + 1; row < first_row; ++row) {
            const char* empty = history.empty() && row == top_ + 1 ? "nothing sent yet" : "";
            out += at(row, 2) + render({{style::kDim, empty}}, width);
        }
        for (size_t i = 0; i < n; ++i)
            out += at(first_row + static_cast<int>(i), 2) +
                   record_line(history[history.size() - n + i], width);
    }

    const std::string line =
        input.editing ? render({{style::kValue, "> " + input.text}, {"\033[7m", " "}}, width)
                      : render({{style::kDim, "press : to type a command (\"help\" lists them)"}}, width);
    if (line != shown_input_) {
        shown_input_ = line;
        out += at(top_ + 1 + log_lines_, 2) + line;
    }
    return out;
}

}  // namespace dash
