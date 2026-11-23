// What the dashboard shows: every row, its label and how its value is
// translated into text. Edit fields.cpp to add, remove or reorder rows.
#pragma once

#include <vector>

#include "dashboard.hpp"
#include "msp/commander.hpp"

namespace dash {

std::vector<Field> header_fields(const msp::MotorTest& motors);
std::vector<Section> sections();

}  // namespace dash
