// fc_bridge v0. Parameter backend:
//   sim:  fc/setpoint_velocity (TwistStamped) -> clamp + timeout -> Gazebo Twist
//         Gazebo odometry -> fc/odom, fc/attitude, fc/range
//   inav: reads INAV over MSP through esp-link (inav_link.*) -> fc/odom,
//         fc/attitude, fc/range, fc/optical_flow, fc/battery, and armed and
//         link state in fc/status. Listen-only: setpoints go nowhere, and
//         fc/arm is refused, since on the real drone only the radio arms.
//         Nothing of the sim (Gazebo topics, enable) exists here.
//   Both: fc/arm, fc/hold (std_srvs/SetBool) and fc/status (drone_interfaces/FcStatus)
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
#include <stdexcept>
#include <string>

#include "drone_interfaces/msg/fc_status.hpp"
#include "drone_interfaces/msg/optical_flow.hpp"
#include "geometry_msgs/msg/quaternion_stamped.hpp"
#include "geometry_msgs/msg/twist.hpp"
#include "geometry_msgs/msg/twist_stamped.hpp"
#include "nav_msgs/msg/odometry.hpp"
#include "inav_link.hpp"
#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/battery_state.hpp"
#include "sensor_msgs/msg/range.hpp"
#include "std_msgs/msg/bool.hpp"
#include "std_srvs/srv/set_bool.hpp"

using namespace std::chrono_literals;
using drone_interfaces::msg::FcStatus;
using drone_interfaces::msg::OpticalFlow;
using geometry_msgs::msg::Quaternion;
using geometry_msgs::msg::QuaternionStamped;
using geometry_msgs::msg::Twist;
using geometry_msgs::msg::TwistStamped;
using nav_msgs::msg::Odometry;
using sensor_msgs::msg::BatteryState;
using sensor_msgs::msg::Range;
using std_msgs::msg::Bool;
using std_srvs::srv::SetBool;

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

Quaternion from_rpy(double roll, double pitch, double yaw)
{
  const double cr = std::cos(roll / 2), sr = std::sin(roll / 2);
  const double cp = std::cos(pitch / 2), sp = std::sin(pitch / 2);
  const double cy = std::cos(yaw / 2), sy = std::sin(yaw / 2);
  Quaternion q;
  q.w = cr * cp * cy + sr * sp * sy;
  q.x = sr * cp * cy - cr * sp * sy;
  q.y = cr * sp * cy + sr * cp * sy;
  q.z = cr * cp * sy - sr * sp * cy;
  return q;
}
}  // namespace

class FcBridge : public rclcpp::Node
{
public:
  FcBridge()
  : Node("fc_bridge")
  {
    backend_ = declare_parameter<std::string>("backend", "sim");
    if (backend_ != "sim" && backend_ != "inav") {
      throw std::invalid_argument("backend must be sim or inav, not '" + backend_ + "'");
    }
    const bool sim = backend_ == "sim";
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
    // keeps defaults for rangefinder vaules as in model VL53L1X
    // overrides rangefinder defaults in drone_bringup/config/sim.yaml
    declare_parameter<double>("range_noise", 0.005);    // m
    declare_parameter<double>("range_min", 0.04);       // m, VL53L1X-like
    declare_parameter<double>("range_max", 4.0);        // m
    declare_parameter<double>("range_fov", 0.47);       // rad, full cone
    // Sim: true when nothing arms it (no radio); the launch sets it. inav: unknown
    // until MSP reports it, so false.
    const bool armed_at_start = declare_parameter<bool>("armed_at_start", true);
    armed_ = sim && armed_at_start;

    if (sim) {
      cmd_pub_ = create_publisher<Twist>(gz_twist_topic, 10);
      enable_pub_ = create_publisher<Bool>(gz_enable_topic, 10);
    }
    odom_pub_ = create_publisher<Odometry>("fc/odom", 10);
    attitude_pub_ = create_publisher<QuaternionStamped>("fc/attitude", 10);
    range_pub_ = create_publisher<Range>("fc/range", 10);
    status_pub_ = create_publisher<FcStatus>("fc/status", 10);
    arm_srv_ = create_service<SetBool>(
      "fc/arm", [this](SetBool::Request::SharedPtr req, SetBool::Response::SharedPtr res) {
        if (backend_ != "sim") {
          // The real drone arms from the radio only; ROS can't arm or disarm it.
          res->success = false;
          res->message = "arming is on the radio (backend " + backend_ + ")";
          RCLCPP_WARN(get_logger(), "fc/arm refused: %s", res->message.c_str());
          return;
        }
        if (armed_ != req->data) {
          armed_ = req->data;
          RCLCPP_INFO(get_logger(), armed_ ? "Armed (fc/arm)" : "Disarmed (fc/arm)");
          keep_enabled();
          publish_status();
        }
        res->success = true;
        res->message = armed_ ? "armed" : "disarmed";
      });
    hold_srv_ = create_service<SetBool>(
      "fc/hold", [this](SetBool::Request::SharedPtr req, SetBool::Response::SharedPtr res) {
        if (holding_ != req->data) {
          holding_ = req->data;
          RCLCPP_WARN(get_logger(), holding_ ?
            "Hold on (fc/hold): ignoring setpoints, sending zero" :
            "Hold off (fc/hold): following setpoints again");
          publish_status();
        }
        res->success = true;
        res->message = holding_ ? "holding" : "not holding";
      });
    if (sim) {
      sim_odom_sub_ = create_subscription<Odometry>(
        sim_odom_topic, rclcpp::SensorDataQoS(),
        [this](const Odometry & msg) {on_sim_odom(msg);});
    } else {
      inav::LinkConfig link;
      link.host = declare_parameter<std::string>("msp_host", link.host);
      link.port = static_cast<uint16_t>(declare_parameter<int>("msp_port", link.port));
      link.reply_timeout_s = declare_parameter<double>("msp_timeout_s", link.reply_timeout_s);
      flow_pub_ = create_publisher<OpticalFlow>("fc/optical_flow", 10);
      battery_pub_ = create_publisher<BatteryState>("fc/battery", 10);
      RCLCPP_INFO(get_logger(), "Backend inav: reading INAV over MSP at %s:%u. Listen-only: "
        "setpoints go nowhere", link.host.c_str(), static_cast<unsigned>(link.port));
      link_ = std::make_unique<inav::InavLink>(
        link, [this](inav::InavLink::Level level, const std::string & text) {
          if (level == inav::InavLink::Level::INFO) {
            RCLCPP_INFO(get_logger(), "%s", text.c_str());
          } else if (level == inav::InavLink::Level::WARN) {
            RCLCPP_WARN(get_logger(), "%s", text.c_str());
          } else {
            RCLCPP_ERROR(get_logger(), "%s", text.c_str());
          }
        });
      link_->start();
      inav_timer_ = create_timer(
        std::chrono::duration<double>(1.0 / rate_hz), [this]() {publish_inav();});
    }

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
    enable_timer_ = create_timer(1s, [this]() {keep_enabled(); publish_status();});
  }

private:
  double param(const std::string & name) {return get_parameter(name).as_double();}

  void keep_enabled()
  {
    // Sim only. On the real drone, arming stays on the radio.
    if (!enable_pub_) {
      return;
    }
    Bool msg;
    msg.data = armed_;
    enable_pub_->publish(msg);
  }

  void publish_status()
  {
    FcStatus st;
    st.header.stamp = now();
    st.backend = backend_;
    st.armed = armed_;
    st.holding = holding_;
    st.following_setpoints = !stale_ && !holding_;
    st.setpoint_age_s = last_rx_ ? static_cast<float>((now() - *last_rx_).seconds()) : -1.0f;
    st.range_valid = range_valid_;
    st.link_ok = true;
    st.state_age_s = 0.0f;
    if (link_) {
      const auto s = link_->state();
      st.link_ok = s.link_ok;
      st.state_age_s = s.last_reply == inav::Clock::time_point{} ? -1.0f :
        static_cast<float>(seconds_since(s.last_reply));
    }
    status_pub_->publish(st);
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
    if (stale_ != !fresh) {
      stale_ = !fresh;
      publish_status();
    }

    if (cmd_pub_) {
      cmd_pub_->publish(fresh && !holding_ ? clamp(last_sp_) : Twist());
    }
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
    //added during MTF-02P rangefinder sim changes
    range.field_of_view = param("range_fov");
    range.variance = std::pow(param("range_noise"), 2);
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
    if (range_valid_ != std::isfinite(range.range)) {
      range_valid_ = std::isfinite(range.range);
      publish_status();
    }
    range_pub_->publish(range);
  }

  static double seconds_since(inav::Clock::time_point t)
  {
    return std::chrono::duration<double>(inav::Clock::now() - t).count();
  }

  // ROS time at which a reply arrived (the link stamps it on a steady clock).
  rclcpp::Time arrival(inav::Clock::time_point t)
  {
    return now() - rclcpp::Duration::from_seconds(seconds_since(t));
  }

  // Publishes what the link received since the last call. INAV's frames are
  // converted here, from the INAV 9.1.0 source (imu.c, the position estimator):
  //   roll and pitch: same sense as ROS (right side down, nose down positive)
  //   yaw: INAV gives a heading growing clockwise; ROS yaw is counter-clockwise
  //   position and velocity: INAV's local frame is North-East-Up; ROS odom here
  //     is x North, y West (= -East), z Up, so yaw 0 points along x
  //   optical flow: INAV's body axes and sign are already the ones
  //     drone_interfaces/OpticalFlow documents, so it passes through
  // To check on the bench: nose up reads negative pitch, turning clockwise
  // seen from above makes ROS yaw decrease.
  void publish_inav()
  {
    const auto s = link_->state();
    bool status_changed = false;

    if (s.status.count != seen_status_ && s.status.value) {
      seen_status_ = s.status.count;
      if (armed_ != s.status.value->armed()) {
        armed_ = s.status.value->armed();
        RCLCPP_INFO(get_logger(), armed_ ? "INAV reports armed" : "INAV reports disarmed");
        status_changed = true;
      }
    }
    if (link_ok_ != s.link_ok) {
      link_ok_ = s.link_ok;
      status_changed = true;
    }

    if (s.pose.count != seen_pose_ && s.pose.value) {
      seen_pose_ = s.pose.count;
      const auto & p = *s.pose.value;
      Odometry odom;
      odom.header.stamp = arrival(s.pose.stamp);
      odom.header.frame_id = "odom";
      odom.child_frame_id = "base_link";
      odom.pose.pose.position.x = p.x;
      odom.pose.pose.position.y = -p.y;
      odom.pose.pose.position.z = p.z;
      const Quaternion q = from_rpy(p.roll, p.pitch, -p.yaw);
      odom.pose.pose.orientation = q;
      // INAV's velocity is in the earth frame; Odometry's twist is in the body
      // frame (as the sim backend publishes it): rotate by the inverse attitude.
      Quaternion inverse = q;
      inverse.x = -q.x; inverse.y = -q.y; inverse.z = -q.z;
      double vx = p.vx, vy = -p.vy, vz = p.vz;
      body_to_world(inverse, vx, vy, vz);
      odom.twist.twist.linear.x = vx;
      odom.twist.twist.linear.y = vy;
      odom.twist.twist.linear.z = vz;
      odom_pub_->publish(odom);

      QuaternionStamped attitude;
      attitude.header = odom.header;
      attitude.quaternion = q;
      attitude_pub_->publish(attitude);
    }

    if (s.flow.count != seen_flow_ && s.flow.value) {
      seen_flow_ = s.flow.count;
      const auto & f = *s.flow.value;
      OpticalFlow flow;
      flow.header.stamp = arrival(s.flow.stamp);
      flow.header.frame_id = "base_link";
      flow.quality = f.quality;
      flow.flow_rate_x = static_cast<float>(f.flow_rate_x);
      flow.flow_rate_y = static_cast<float>(f.flow_rate_y);
      flow.body_rate_x = static_cast<float>(f.body_rate_x);
      flow.body_rate_y = static_cast<float>(f.body_rate_y);
      flow_pub_->publish(flow);
    }

    if (s.range.count != seen_range_ && s.range.value) {
      seen_range_ = s.range.count;
      // INAV reports 0 cm, which looks like a distance, when no rangefinder
      // runs: only trust the reading while the status says one is fitted.
      const bool fitted = s.status.value && s.status.value->rangefinder_present();
      const auto state = s.range.value->state;
      if (fitted && state != inav::Rangefinder::State::NO_READING) {
        Range range;
        range.header.stamp = arrival(s.range.stamp);
        range.header.frame_id = "rangefinder";
        range.radiation_type = Range::INFRARED;
        range.field_of_view = param("range_fov");
        range.min_range = param("range_min");
        range.max_range = param("range_max");
        range.range = state == inav::Rangefinder::State::VALID ?
          static_cast<float>(s.range.value->distance_m) :
          std::numeric_limits<float>::infinity();   // REP 117: nothing in range
        range_pub_->publish(range);
        if (range_valid_ != std::isfinite(range.range)) {
          range_valid_ = std::isfinite(range.range);
          status_changed = true;
        }
      } else if (range_valid_) {
        range_valid_ = false;
        status_changed = true;
      }
    }

    if (s.analog.count != seen_analog_ && s.analog.value) {
      seen_analog_ = s.analog.count;
      const auto & a = *s.analog.value;
      BatteryState battery;
      battery.header.stamp = arrival(s.analog.stamp);
      battery.voltage = static_cast<float>(a.voltage_v);
      battery.current = static_cast<float>(-a.current_a);   // ROS: negative while discharging
      battery.percentage = a.battery_pct / 100.0f;
      battery.present = a.battery_state != 3;               // 3: not present
      battery.power_supply_status = BatteryState::POWER_SUPPLY_STATUS_DISCHARGING;
      battery.power_supply_technology = BatteryState::POWER_SUPPLY_TECHNOLOGY_LIPO;
      battery.power_supply_health = a.battery_state == 2 ?   // 2: critical
        BatteryState::POWER_SUPPLY_HEALTH_DEAD : BatteryState::POWER_SUPPLY_HEALTH_GOOD;
      battery.charge = std::numeric_limits<float>::quiet_NaN();
      battery.capacity = std::numeric_limits<float>::quiet_NaN();
      battery.design_capacity = std::numeric_limits<float>::quiet_NaN();
      battery.temperature = std::numeric_limits<float>::quiet_NaN();
      battery.cell_voltage.assign(a.cell_count, std::numeric_limits<float>::quiet_NaN());
      battery_pub_->publish(battery);
    }

    if (status_changed) {
      publish_status();
    }
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
  rclcpp::Publisher<FcStatus>::SharedPtr status_pub_;
  rclcpp::Publisher<OpticalFlow>::SharedPtr flow_pub_;
  rclcpp::Publisher<BatteryState>::SharedPtr battery_pub_;
  rclcpp::Service<SetBool>::SharedPtr arm_srv_;
  rclcpp::Service<SetBool>::SharedPtr hold_srv_;
  rclcpp::Subscription<TwistStamped>::SharedPtr sub_;
  rclcpp::TimerBase::SharedPtr tick_timer_;
  rclcpp::TimerBase::SharedPtr enable_timer_;
  rclcpp::TimerBase::SharedPtr inav_timer_;
  std::unique_ptr<inav::InavLink> link_;   // inav only
  bool link_ok_{false};
  uint64_t seen_status_{0}, seen_pose_{0}, seen_flow_{0}, seen_range_{0}, seen_analog_{0};

  std::string backend_;
  Twist last_sp_;
  std::optional<rclcpp::Time> last_rx_;
  bool stale_{true};
  bool armed_{true};
  bool holding_{false};
  bool range_valid_{false};

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