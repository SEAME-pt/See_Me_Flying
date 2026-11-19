cmake_minimum_required(VERSION 3.16)
project(msp_dashboard LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(NOT CMAKE_BUILD_TYPE)
  set(CMAKE_BUILD_TYPE Release)
endif()

# MSP protocol, decoders and telemetry state. No terminal code in here, so a
# ROS 2 node can link this library later.
add_library(msp_core STATIC
  src/msp/transport.cpp
  src/msp/client.cpp
  src/msp/messages.cpp
  src/msp/poller.cpp
  src/msp/commander.cpp
  src/msp/frame.cpp
)
target_include_directories(msp_core PUBLIC include)
target_compile_options(msp_core PRIVATE -Wall -Wextra -Wpedantic)

add_executable(msp_dashboard
  src/dashboard/main.cpp
  src/dashboard/dashboard.cpp
  src/dashboard/fields.cpp
  src/dashboard/terminal.cpp
  src/dashboard/command_panel.cpp
  src/dashboard/console.cpp
)
target_link_libraries(msp_dashboard PRIVATE msp_core)
target_compile_options(msp_dashboard PRIVATE -Wall -Wextra -Wpedantic)

# The single owner of the MSP link: queues, routes and logs every frame.
add_executable(msp_gateway src/gateway/main.cpp)
target_link_libraries(msp_gateway PRIVATE msp_core)
target_compile_options(msp_gateway PRIVATE -Wall -Wextra -Wpedantic)
