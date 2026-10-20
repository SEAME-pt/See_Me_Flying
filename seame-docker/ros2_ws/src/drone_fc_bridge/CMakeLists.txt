cmake_minimum_required(VERSION 3.8)
project(drone_fc_bridge)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
if(CMAKE_CXX_COMPILER_ID MATCHES "GNU|Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(std_msgs REQUIRED)

add_executable(fc_bridge src/fc_bridge.cpp)
target_link_libraries(fc_bridge PUBLIC
  rclcpp::rclcpp
  ${geometry_msgs_TARGETS}
  ${std_msgs_TARGETS})

install(TARGETS fc_bridge DESTINATION lib/${PROJECT_NAME})

ament_package()