#include "dashboard.hpp"

#include <algorithm>

namespace dash {

namespace {

constexpr int kLabelWidth = 18;
constexpr int kMinValueWidth = 22;
constexpr int kColumnGap = 3;
constexpr int kLeft = 2;   // first screen column used

bool is_continuation(unsigned char c) { return (c & 0xC0) == 0x80; }

std::string section_rule(const std::string& title, int width) {
    std::string s = "── " + title + " ";
    for (int w = display_width(s); w < width; ++w) s += "─";
    return s;
}

}  // namespace

std::string at(int row, int col) {
    return "\033[" + std::to_string(row) + ";" + std::to_string(col) + "H";
}

int display_width(const std::string& s) {
    return static_cast<int>(std::count_if(s.begin(), s.end(),
                                          [](char c) { return !is_continuation(static_cast<unsigned char>(c)); }));
}

std::string fit(const std::string& s, int width) {
    if (width <= 0) return "";
    const int w = display_width(s);
    if (w <= width) return s + std::string(static_cast<size_t>(width - w), ' ');
    std::string out;
    int used = 0;
    for (size_t i = 0; i < s.size(); ++i) {
        const auto c = static_cast<unsigned char>(s[i]);
        if (!is_continuation(c)) {
            if (used == width - 1) break;
            ++used;
        }
        out += s[i];
    }
    return out + "…";
}

Dashboard::Dashboard(std::vector<Field> header, std::vector<Section> sections)
    : header_(std::move(header)), sections_(std::move(sections)) {}

std::string Dashboard::layout(int cols, int rows) {
    placed_.clear();
    std::string out = "\033[0m\033[2J";
    const int footer_row = rows;
    int hidden = 0;

    // Title bar.
    const std::string hint = ": command   space STOP motors   q quit ";
    out += at(1, 1) + style::kTitle + fit(" INAV MSP dashboard", cols - display_width(hint)) +
           style::kDim + hint + style::kReset;

    // Full-width header rows.
    int row = 3;
    const int header_value_width = std::max(10, cols - kLeft - kLabelWidth);
    for (const Field& f : header_) {
        if (row >= footer_row) {
            ++hidden;
            continue;
        }
        out += at(row, kLeft) + style::kLabel + fit(f.label, kLabelWidth - 1) + style::kReset;
        placed_.push_back({&f, row, kLeft + kLabelWidth, header_value_width, ""});
        ++row;
    }
    const int top = row + 1;

    // Sections flow into as many columns as fit; each goes to the shortest column.
    const int usable = cols - kLeft;
    const int ncols = std::max(1, (usable + kColumnGap) / (kLabelWidth + kMinValueWidth + kColumnGap));
    const int col_width = (usable - (ncols - 1) * kColumnGap) / ncols;
    const int value_width = col_width - kLabelWidth;
    std::vector<int> heights(static_cast<size_t>(ncols), 0);

    for (const Section& s : sections_) {
        const auto c = static_cast<size_t>(std::min_element(heights.begin(), heights.end()) - heights.begin());
        const int x = kLeft + static_cast<int>(c) * (col_width + kColumnGap);
        int y = top + heights[c];

        if (y < footer_row) out += at(y, x) + style::kSection + section_rule(s.title, col_width - 1) + style::kReset;
        ++y;
        for (const Field& f : s.fields) {
            if (y < footer_row) {
                out += at(y, x) + style::kLabel + fit(f.label, kLabelWidth - 1) + style::kReset;
                placed_.push_back({&f, y, x + kLabelWidth, value_width, ""});
            } else {
                ++hidden;
            }
            ++y;
        }
        heights[c] += static_cast<int>(s.fields.size()) + 2;  // title + fields + spacer
    }

    if (hidden > 0)
        out += at(footer_row, kLeft) + style::kWarn + "terminal too small: " + std::to_string(hidden) +
               " fields hidden - enlarge it or reduce the font size" + style::kReset;
    return out;
}

std::string Dashboard::update(const msp::Telemetry& t) {
    std::string out;
    for (Placed& p : placed_) {
        const Cell cell = p.field->get(t);
        const std::string text = fit(cell.text, p.width - 1);  // keep a 1-column margin
        std::string shown = std::string(cell.style) + text;
        if (shown == p.last) continue;   // unchanged: don't touch the screen
        out += at(p.row, p.col) + shown + style::kReset;
        p.last = std::move(shown);
    }
    return out;
}

}  // namespace dash
