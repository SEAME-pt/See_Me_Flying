"""
Whole first flight in one command.

Order: Gazebo, bridge, fc_bridge and watchdog start together; after 5 s
(wall time, so Gazebo has loaded), setpoint_pub starts: takeoff, then circles.
"""
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

SIM = {'use_sim_time': True}
SETPOINT_TOPIC = ('setpoint_velocity', '/fc/setpoint_velocity')


def generate_launch_description():
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution(
            [FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py'])),
        launch_arguments={'gz_args': '-r multicopter_velocity_control.sdf'}.items(),
    )

    bridge = Node(
        package='ros_gz_bridge', executable='parameter_bridge',
        arguments=[
            '/X3/gazebo/command/twist@geometry_msgs/msg/Twist]gz.msgs.Twist',
            '/X3/enable@std_msgs/msg/Bool]gz.msgs.Boolean',
            '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock',
        ],
        output='screen',
    )

    fc_bridge = Node(
        package='drone_fc_bridge', executable='fc_bridge',
        parameters=[SIM], output='screen',
    )

    watchdog = Node(
        package='drone_basics_cpp', executable='watchdog',
        remappings=[SETPOINT_TOPIC],
        parameters=[SIM], output='screen',
    )

    setpoints = TimerAction(period=5.0, actions=[Node(
        package='drone_basics_py', executable='setpoint_pub',
        remappings=[SETPOINT_TOPIC],
        parameters=[SIM], output='screen',
    )])

    return LaunchDescription([gazebo, bridge, fc_bridge, watchdog, setpoints])
