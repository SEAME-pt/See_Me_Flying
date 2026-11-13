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
find_package(nav_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)
find_package(std_srvs REQUIRED)
find_package(drone_interfaces REQUIRED)

add_executable(fc_bridge src/fc_bridge.cpp)
target_link_libraries(fc_bridge PUBLIC
  rclcpp::rclcpp
  ${geometry_msgs_TARGETS}
  ${nav_msgs_TARGETS}
  ${sensor_msgs_TARGETS}
  ${std_msgs_TARGETS}
  ${std_srvs_TARGETS}
  ${drone_interfaces_TARGETS})

install(TARGETS fc_bridge DESTINATION lib/${PROJECT_NAME})

# MSP framing, INAV decoders and the TCP link for the inav backend. No ROS in
# it, so the tests below run it against captured frames and a fake FC. Not
# linked into fc_bridge yet.
find_package(Threads REQUIRED)
add_library(fc_msp STATIC src/msp.cpp src/inav_decode.cpp src/inav_link.cpp)
target_include_directories(fc_msp PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(fc_msp PUBLIC Threads::Threads)

if(BUILD_TESTING)
  find_package(launch_testing_ament_cmake REQUIRED)
  # Own domain and localhost only, so a running sim (domain 6) cannot interfere.
  add_launch_test(test/test_failsafes.py TIMEOUT 120
    ENV ROS_DOMAIN_ID=199 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
  add_launch_test(test/test_state.py TIMEOUT 120
    ENV ROS_DOMAIN_ID=199 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
  add_launch_test(test/test_services.py TIMEOUT 120
    ENV ROS_DOMAIN_ID=199 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
  add_launch_test(test/test_inav.py TIMEOUT 120
    ENV ROS_DOMAIN_ID=199 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)

  # Captured frames from the real drone live in test/data (see its README).
  find_package(ament_cmake_gtest REQUIRED)
  foreach(name test_msp test_inav_decode test_inav_link)
    ament_add_gtest(${name} test/${name}.cpp)
    target_link_libraries(${name} fc_msp)
    target_compile_definitions(${name} PRIVATE
      TEST_DATA_DIR="${CMAKE_CURRENT_SOURCE_DIR}/test/data")
  endforeach()
endif()

ament_package()