#include <chrono>
#include <memory>

#include "geometry_msgs/msg/twist_stamped.hpp"
#include "rclcpp/rclcpp.hpp"

using namespace std::chrono_literals;

class Watchdog : public rclcpp::Node
{
public:
  Watchdog() : Node("watchdog")
  {
    timeout_s_ = declare_parameter<double>("timeout_s", 0.5);
    last_rx_ = now();
    sub_ = create_subscription<geometry_msgs::msg::TwistStamped>(
      "setpoint_velocity", rclcpp::SensorDataQoS(),
      [this](const geometry_msgs::msg::TwistStamped &) { last_rx_ = now(); });
    timer_ = create_timer(100ms, [this]() { check(); });
  }

private:
  void check()
  {
    const double age = (now() - last_rx_).seconds();
    const bool stale = age > timeout_s_;
    if (stale && !stale_) {
      RCLCPP_WARN(get_logger(), "No setpoint for %.2f s: a real failsafe would command hover", age);
    } else if (!stale && stale_) {
      RCLCPP_INFO(get_logger(), "Setpoints are back");
    }
    stale_ = stale;
  }

  double timeout_s_{0.5};
  bool stale_{false};
  rclcpp::Time last_rx_{0, 0, RCL_ROS_TIME};
  rclcpp::Subscription<geometry_msgs::msg::TwistStamped>::SharedPtr sub_;
  rclcpp::TimerBase::SharedPtr timer_;
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<Watchdog>());
  rclcpp::shutdown();
  return 0;
}