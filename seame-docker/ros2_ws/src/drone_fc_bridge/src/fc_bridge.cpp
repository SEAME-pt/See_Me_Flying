// fc_bridge v0, sim backend:
//   fc/setpoint_velocity (TwistStamped) -> clamp + timeout -> Gazebo Twist
//
// Publishes every tick, not only on new setpoints: Gazebo's velocity
// controller keeps following the last command it got, so on timeout we
// must actively send zero. That explicit zero is the failsafe.

#include <algorithm>
#include <chrono>
#include <cmath>
#include <memory>
#include <optional>
#include <string>

#include "geometry_msgs/msg/twist.hpp"
#include "geometry_msgs/msg/twist_stamped.hpp"
#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/bool.hpp"

using namespace std::chrono_literals;
using geometry_msgs::msg::Twist;
using geometry_msgs::msg::TwistStamped;
using std_msgs::msg::Bool;

namespace
{
bool all_finite(const Twist & t)
{
  return std::isfinite(t.linear.x) && std::isfinite(t.linear.y) &&
         std::isfinite(t.linear.z) && std::isfinite(t.angular.x) &&
         std::isfinite(t.angular.y) && std::isfinite(t.angular.z);
}
}  // namespace

class FcBridge : public rclcpp::Node
{
public:
  FcBridge()
  : Node("fc_bridge")
  {
    const auto gz_twist_topic =
      declare_parameter<std::string>("gz_twist_topic", "/X3/gazebo/command/twist");
    const auto gz_enable_topic =
      declare_parameter<std::string>("gz_enable_topic", "/X3/enable");
    const double rate_hz = declare_parameter<double>("rate_hz", 20.0);
    declare_parameter<double>("setpoint_timeout_s", 0.3);
    declare_parameter<double>("max_speed_xy", 0.5);   // m/s
    declare_parameter<double>("max_speed_z", 0.3);    // m/s
    declare_parameter<double>("max_yaw_rate", 1.0);   // rad/s
    
    cmd_pub_ = create_publisher<Twist>(gz_twist_topic, 10);
    enable_pub_ = create_publisher<Bool>(gz_enable_topic, 10);

    sub_ = create_subscription<TwistStamped>(
      "fc/setpoint_velocity", rclcpp::SensorDataQoS(),
      [this](const TwistStamped & msg) {
        if (!all_finite(msg.twist)) {
          RCLCPP_WARN_THROTTLE(get_logger(), *get_clock(), 1000,
            "Rejected non-finite setpoint (NaN/inf): treating as stale");
          return;   // last_sp_ and last_rx_ unchanged, so the timeout still fires
        }
        last_sp_ = msg.twist;
        last_rx_ = now();
      });

    // create_timer runs on the node clock, so it follows Gazebo's /clock
    // when use_sim_time is true (and stops while the sim is paused).
    tick_timer_ = create_timer(
      std::chrono::duration<double>(1.0 / rate_hz), [this]() {tick();});
    enable_timer_ = create_timer(1s, [this]() {keep_enabled();});
  }

private:
  double param(const std::string & name) {return get_parameter(name).as_double();}

  void keep_enabled()
  {
    // Sim only. On the real drone, arming stays on the radio.
    Bool msg;
    msg.data = true;
    enable_pub_->publish(msg);
  }

  void tick()
  {
    bool fresh = false;
    if (last_rx_) {
      const double age = (now() - *last_rx_).seconds();
      fresh = age >= 0.0 && age <= param("setpoint_timeout_s");  // age < 0: sim time was reset
    }

    if (fresh && stale_) {
      RCLCPP_INFO(get_logger(), "Setpoints received, following them");
    } else if (!fresh && !stale_) {
      RCLCPP_WARN(get_logger(), "Setpoint timeout: holding (zero velocity)");
    }
    stale_ = !fresh;

    cmd_pub_->publish(fresh ? clamp(last_sp_) : Twist());
  }

  Twist clamp(const Twist & in)
  {
    Twist out;

    // Horizontal: cap the speed, keep the direction.
    const double vmax = param("max_speed_xy");
    const double norm = std::hypot(in.linear.x, in.linear.y);
    const double scale = (norm > vmax && norm > 0.0) ? vmax / norm : 1.0;
    out.linear.x = in.linear.x * scale;
    out.linear.y = in.linear.y * scale;

    const double zmax = param("max_speed_z");
    out.linear.z = std::clamp(in.linear.z, -zmax, zmax);

    const double wmax = param("max_yaw_rate");
    out.angular.z = std::clamp(in.angular.z, -wmax, wmax);

    return out;
  }

  rclcpp::Publisher<Twist>::SharedPtr cmd_pub_;
  rclcpp::Publisher<Bool>::SharedPtr enable_pub_;
  rclcpp::Subscription<TwistStamped>::SharedPtr sub_;
  rclcpp::TimerBase::SharedPtr tick_timer_;
  rclcpp::TimerBase::SharedPtr enable_timer_;

  Twist last_sp_;
  std::optional<rclcpp::Time> last_rx_;
  bool stale_{true};
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<FcBridge>());
  rclcpp::shutdown();
  return 0;
}