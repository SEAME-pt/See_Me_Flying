from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    params = PathJoinSubstitution(
        [FindPackageShare('drone_bringup'), 'config', 'basics.yaml'])

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='false'),
        Node(
            package='drone_basics_py',
            executable='setpoint_pub',
            parameters=[params, {'use_sim_time': use_sim_time}],
            output='screen',
        ),
        Node(
            package='drone_basics_cpp',
            executable='watchdog',
            parameters=[params, {'use_sim_time': use_sim_time}],
            output='screen',
        ),
    ])