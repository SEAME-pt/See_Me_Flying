// Table layout: labels and section titles are drawn once; afterwards only the
// value cells whose text or color changed are rewritten in place.
#pragma once

#include <functional>
#include <string>
#include <vector>

#include "msp/telemetry.hpp"

namespace dash {

namespace style {
constexpr const char* kReset = "\033[0m";
constexpr const char* kTitle = "\033[1;97m";
constexpr const char* kSection = "\033[1;36m";
constexpr const char* kLabel = "\033[94m";
constexpr const char* kValue = "\033[97m";
constexpr const char* kDim = "\033[2;37m";
constexpr const char* kGood = "\033[92m";
constexpr const char* kWarn = "\033[93m";
constexpr const char* kBad = "\033[1;91m";
}  // namespace style

struct Cell {
    std::string text;
    const char* style = style::kValue;
};

using Getter = std::function<Cell(const msp::Telemetry&)>;

struct Field {
    std::string label;
    Getter get;
};

struct Section {
    std::string title;
    std::vector<Field> fields;
};

class Dashboard {
public:
    // header: full-width rows at the top; sections: flowed into columns.
    Dashboard(std::vector<Field> header, std::vector<Section> sections);

    // Clears the screen and draws the static parts for this terminal size.
    // Returns the escape sequence to write.
    std::string layout(int cols, int rows);
    // Returns escape sequences that rewrite only the values that changed.
    std::string update(const msp::Telemetry& t);

private:
    struct Placed {
        const Field* field;
        int row, col, width;
        std::string last;   // style + text currently on screen
    };

    std::vector<Field> header_;
    std::vector<Section> sections_;
    std::vector<Placed> placed_;
};

// Escape sequence that moves the cursor (1-based row/col).
std::string at(int row, int col);
// Terminal columns taken by a UTF-8 string (one per code point).
int display_width(const std::string& s);
// Pads or truncates to exactly `width` terminal columns (UTF-8 aware).
std::string fit(const std::string& s, int width);

}  // namespace dash
