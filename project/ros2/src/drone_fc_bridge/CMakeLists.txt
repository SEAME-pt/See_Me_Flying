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

# MSP framing, INAV decoders, the stick mapping and the TCP link for the inav
# backend. No ROS in it, so the tests below run it against captured frames and
# a fake FC.
find_package(Threads REQUIRED)
add_library(fc_msp STATIC
  src/msp.cpp src/inav_decode.cpp src/inav_link.cpp src/inav_sticks.cpp)
target_include_directories(fc_msp PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/src)
target_link_libraries(fc_msp PUBLIC Threads::Threads)

add_executable(fc_bridge src/fc_bridge.cpp)
target_link_libraries(fc_bridge PUBLIC
  fc_msp
  rclcpp::rclcpp
  ${geometry_msgs_TARGETS}
  ${nav_msgs_TARGETS}
  ${sensor_msgs_TARGETS}
  ${std_msgs_TARGETS}
  ${std_srvs_TARGETS}
  ${drone_interfaces_TARGETS})

# watchdog: warns when the setpoint stream to fc_bridge stops, and when it is back.
# Only watches; fc_bridge's own timeout is what sends zero.
add_executable(watchdog src/watchdog.cpp)
target_link_libraries(watchdog PUBLIC rclcpp::rclcpp ${geometry_msgs_TARGETS})

<<<<<<< HEAD:project/ros2/src/drone_fc_bridge/CMakeLists.txt
install(TARGETS fc_bridge watchdog DESTINATION lib/${PROJECT_NAME})

=======
>>>>>>> origin/main:seame-docker/ros2_ws/src/drone_fc_bridge/CMakeLists.txt
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
  add_launch_test(test/test_inav_state.py TIMEOUT 120
    ENV ROS_DOMAIN_ID=199 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
  add_launch_test(test/test_inav_rc.py TIMEOUT 120
    ENV ROS_DOMAIN_ID=199 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
<<<<<<< HEAD:project/ros2/src/drone_fc_bridge/CMakeLists.txt
  add_launch_test(test/test_watchdog.py TIMEOUT 60
    ENV ROS_DOMAIN_ID=199 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
=======
>>>>>>> origin/main:seame-docker/ros2_ws/src/drone_fc_bridge/CMakeLists.txt

  # Captured frames from the real drone live in test/data (see its README).
  find_package(ament_cmake_gtest REQUIRED)
  foreach(name test_msp test_inav_decode test_inav_link test_inav_sticks)
    ament_add_gtest(${name} test/${name}.cpp)
    target_link_libraries(${name} fc_msp)
    target_compile_definitions(${name} PRIVATE
      TEST_DATA_DIR="${CMAKE_CURRENT_SOURCE_DIR}/test/data")
  endforeach()
endif()

ament_package()