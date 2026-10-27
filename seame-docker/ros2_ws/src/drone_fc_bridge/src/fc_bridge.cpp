// fc_bridge v0, sim backend:
//   fc/setpoint_velocity (TwistStamped) -> clamp + timeout -> Gazebo Twist
//   Gazebo odometry -> fc/odom, fc/attitude, fc/range
//
// Publishes every tick, not only on new setpoints: Gazebo's velocity
// controller keeps following the last command it got, so on timeout we
// must actively send zero. That explicit zero is the failsafe.
//
// State is shaped like what INAV reports with optical flow + rangefinder,
// not like the perfect pose Gazebo knows: horizontal position is integrated
// from noisy velocity and drifts, and height comes from a rangefinder with
// limits. Code above fc_bridge then can't come to rely on what the real
// drone won't have.

#include <algorithm>
#include <chrono>
#include <cmath>
#include <limits>
#include <memory>
#include <optional>
#include <random>
#include <string>

#include "geometry_msgs/msg/quaternion_stamped.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "geometry_msgs/msg/twist_stamped.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/range.hpp"
#include "std_msgs/msg/bool.hpp"

using namespace std::chrono_literals;
using geometry_msgs::msg::Quaternion;
using geometry_msgs::msg::QuaternionStamped;
using geometry_msgs::msg::Twist;
using geometry_msgs::msg::TwistStamped;
using nav_msgs::msg::Odometry;
using sensor_msgs::msg::Range;
using std_msgs::msg::Bool;

namespace
{
bool all_finite(const Twist & t)
{
  return std::isfinite(t.linear.x) && std::isfinite(t.linear.y) &&
         std::isfinite(t.linear.z) && std::isfinite(t.angular.x) &&
         std::isfinite(t.angular.y) && std::isfinite(t.angular.z);
}

// Rotate a body-frame vector into the world frame: v' = q v q*.
void body_to_world(const Quaternion & q, double & x, double & y, double & z)
{
  const double tx = 2.0 * (q.y * z - q.z * y);
  const double ty = 2.0 * (q.z * x - q.x * z);
  const double tz = 2.0 * (q.x * y - q.y * x);
  const double rx = x + q.w * tx + (q.y * tz - q.z * ty);
  const double ry = y + q.w * ty + (q.z * tx - q.x * tz);
  const double rz = z + q.w * tz + (q.x * ty - q.y * tx);
  x = rx; y = ry; z = rz;
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
    const auto sim_odom_topic =
      declare_parameter<std::string>("sim_odom_topic", "/X3/odom");
    declare_parameter<double>("flow_vel_noise", 0.02);  // m/s, white noise on velocity
    declare_parameter<double>("flow_drift", 0.002);     // m/s per sqrt(s), random-walk bias
    declare_parameter<double>("range_noise", 0.005);    // m
    declare_parameter<double>("range_min", 0.04);       // m, VL53L1X-like
    declare_parameter<double>("range_max", 4.0);        // m

    cmd_pub_ = create_publisher<Twist>(gz_twist_topic, 10);
    enable_pub_ = create_publisher<Bool>(gz_enable_topic, 10);
    odom_pub_ = create_publisher<Odometry>("fc/odom", 10);
    attitude_pub_ = create_publisher<QuaternionStamped>("fc/attitude", 10);
    range_pub_ = create_publisher<Range>("fc/range", 10);
    sim_odom_sub_ = create_subscription<Odometry>(
      sim_odom_topic, rclcpp::SensorDataQoS(),
      [this](const Odometry & msg) {on_sim_odom(msg);});

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

  double noise(double stddev)
  {
    return stddev > 0.0 ? stddev * normal_(rng_) : 0.0;
  }

  void on_sim_odom(const Odometry & sim)
  {
    const rclcpp::Time stamp(sim.header.stamp);
    double dt = 0.0;
    if (last_odom_stamp_) {
      dt = (stamp - *last_odom_stamp_).seconds();
      if (dt <= 0.0 || dt > 0.5) {
        dt = 0.0;   // sim reset or a gap: don't integrate across it
      }
    }
    last_odom_stamp_ = stamp;
    const auto & q = sim.pose.pose.orientation;

    // Velocity as optical flow would measure it: body frame, noisy, with a
    // slowly wandering bias (the bias is what makes position drift).
    const double drift = param("flow_drift") * std::sqrt(dt);
    bias_x_ += noise(drift);
    bias_y_ += noise(drift);
    const double vn = param("flow_vel_noise");
    double vx = sim.twist.twist.linear.x + bias_x_ + noise(vn);
    double vy = sim.twist.twist.linear.y + bias_y_ + noise(vn);
    double vz = sim.twist.twist.linear.z + noise(vn);

    // Horizontal position: integrated from that velocity, never Gazebo's x, y.
    double wx = vx, wy = vy, wz = vz;
    body_to_world(q, wx, wy, wz);
    pos_x_ += wx * dt;
    pos_y_ += wy * dt;

    Odometry odom;
    odom.header.stamp = sim.header.stamp;
    odom.header.frame_id = "odom";
    odom.child_frame_id = "base_link";
    odom.pose.pose.position.x = pos_x_;
    odom.pose.pose.position.y = pos_y_;
    odom.pose.pose.position.z = sim.pose.pose.position.z;
    odom.pose.pose.orientation = q;
    odom.twist.twist.linear.x = vx;
    odom.twist.twist.linear.y = vy;
    odom.twist.twist.linear.z = vz;
    odom.twist.twist.angular = sim.twist.twist.angular;
    odom_pub_->publish(odom);

    QuaternionStamped attitude;
    attitude.header = odom.header;
    attitude.quaternion = q;
    attitude_pub_->publish(attitude);

    // Rangefinder pointing down the body z axis: reads longer when tilted.
    // up_z is the world z component of the body z axis (1 when level).
    Range range;
    range.header.stamp = sim.header.stamp;
    range.header.frame_id = "rangefinder";
    range.radiation_type = Range::INFRARED;
    range.field_of_view = 0.47;   // rad, about 27 degrees
    range.min_range = param("range_min");
    range.max_range = param("range_max");
    const double up_z = 1.0 - 2.0 * (q.x * q.x + q.y * q.y);
    const double r = up_z > 0.0 ?
      sim.pose.pose.position.z / up_z + noise(param("range_noise")) :
      std::numeric_limits<double>::infinity();   // upside down: no ground
    if (r > range.max_range) {
      range.range = std::numeric_limits<float>::infinity();    // REP 117: nothing in range
    } else if (r < range.min_range) {
      range.range = -std::numeric_limits<float>::infinity();   // REP 117: too close
    } else {
      range.range = r;
    }
    range_pub_->publish(range);
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
  rclcpp::Publisher<Odometry>::SharedPtr odom_pub_;
  rclcpp::Publisher<QuaternionStamped>::SharedPtr attitude_pub_;
  rclcpp::Publisher<Range>::SharedPtr range_pub_;
  rclcpp::Subscription<Odometry>::SharedPtr sim_odom_sub_;
  rclcpp::Subscription<TwistStamped>::SharedPtr sub_;
  rclcpp::TimerBase::SharedPtr tick_timer_;
  rclcpp::TimerBase::SharedPtr enable_timer_;

  Twist last_sp_;
  std::optional<rclcpp::Time> last_rx_;
  bool stale_{true};

  std::mt19937 rng_{42};   // fixed seed: the same run drifts the same way
  std::normal_distribution<double> normal_{0.0, 1.0};
  std::optional<rclcpp::Time> last_odom_stamp_;
  double pos_x_{0.0}, pos_y_{0.0};
  double bias_x_{0.0}, bias_y_{0.0};
};

int main(int argc, char ** argv)
{
  rclcpp::init(argc, argv);
  rclcpp::spin(std::make_shared<FcBridge>());
  rclcpp::shutdown();
  return 0;
}