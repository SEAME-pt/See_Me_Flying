cmake_minimum_required(VERSION 3.20)
project(drone_bringup)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

# find dependencies
find_package(ament_cmake REQUIRED)
# uncomment the following section in order to fill in
# further dependencies manually.
# find_package(<dependency> REQUIRED)

################################################################

# install(DIRECTORY launch config DESTINATION share/${PROJECT_NAME})
install(DIRECTORY launch config worlds models DESTINATION share/${PROJECT_NAME})

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  # the following line skips the linter which checks for copyrights
  # comment the line when a copyright and license is added to all source files
  set(ament_cmake_copyright_FOUND TRUE)
  # the following line skips cpplint (only works in a git repo)
  # comment the line when this package is in a git repo and when
  # a copyright and license is added to all source files
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()

  # Drone limits: values in config/sim.yaml that must agree across nodes.
  find_package(ament_cmake_pytest REQUIRED)
  ament_add_pytest_test(test_config test/test_config.py TIMEOUT 30)
  # What sim.launch.py starts for every combination of arguments, without starting it.
  ament_add_pytest_test(test_launch_files test/test_launch_files.py TIMEOUT 60)
  # The Gazebo worlds: the drone is in each one and wired to gz_bridge.yaml (SDF only).
  ament_add_pytest_test(test_worlds test/test_worlds.py TIMEOUT 30)

  # The whole stack without Gazebo: mission, safety_manager and fc_bridge with a fake drone.
  # Own domain and localhost only, so a running sim (domain 6) cannot interfere.
  find_package(launch_testing_ament_cmake REQUIRED)
  add_launch_test(test/test_stack.py TIMEOUT 180
    ENV ROS_DOMAIN_ID=198 ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST)
endif()

ament_package()
