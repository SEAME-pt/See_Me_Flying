from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EqualsSubstitution, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

SIM = {'use_sim_time': True}
CONTRACT = [('setpoint_velocity', '/fc/setpoint_velocity')]


def is_source(name):
    return IfCondition(EqualsSubstitution(LaunchConfiguration('source'), name))


def generate_launch_description():
    bringup = FindPackageShare('drone_bringup')
    params = PathJoinSubstitution([bringup, 'config', 'sim.yaml'])
    bridge_cfg = PathJoinSubstitution([bringup, 'config', 'gz_bridge.yaml'])

    args = [
        DeclareLaunchArgument('source', default_value='circle',
                              choices=['circle', 'joy', 'none'],
                              description='Who commands the drone'),
        DeclareLaunchArgument('world', default_value='multicopter_velocity_control.sdf',
                              description='SDF world file name or full path'),
    ]

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(PathJoinSubstitution(
            [FindPackageShare('ros_gz_sim'), 'launch', 'gz_sim.launch.py'])),
        launch_arguments={'gz_args': ['-r ', LaunchConfiguration('world')]}.items(),
    )

    bridge = Node(
        package='ros_gz_bridge', executable='parameter_bridge',
        parameters=[{'config_file': bridge_cfg}], output='screen',
    )

    fc_bridge = Node(
        package='drone_fc_bridge', executable='fc_bridge',
        parameters=[params, SIM], output='screen',
    )

    watchdog = Node(
        package='drone_basics_cpp', executable='watchdog',
        remappings=CONTRACT, parameters=[params, SIM], output='screen',
    )

    # source:=circle — takeoff then circles, 5 s after the rest (as today)
    circle = TimerAction(period=5.0, condition=is_source('circle'), actions=[Node(
        package='drone_basics_py', executable='setpoint_pub',
        remappings=CONTRACT, parameters=[params, SIM], output='screen',
    )])

    # source:=joy — RadioMaster Pocket over USB (step 7)
    joy = Node(
        package='joy', executable='joy_node',
        parameters=[params], output='screen', condition=is_source('joy'),
    )
    radio = Node(
        package='drone_basics_py', executable='radio_teleop',
        remappings=CONTRACT, parameters=[params, SIM], output='screen',
        condition=is_source('joy'),
    )

    return LaunchDescription(args + [gazebo, bridge, fc_bridge, watchdog, circle, joy, radio])