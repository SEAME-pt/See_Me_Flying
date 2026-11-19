// Text commands typed in the dashboard. Add new commands in console.cpp.
#pragma once

#include <string>

#include "msp/commander.hpp"
#include "msp/telemetry.hpp"

namespace dash {

void run_command(const std::string& line, const msp::Telemetry& telemetry,
                 msp::Commander& commander, msp::MotorTest& motors);

}  // namespace dash
