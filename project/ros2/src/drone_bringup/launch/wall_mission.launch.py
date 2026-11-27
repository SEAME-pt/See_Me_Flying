"""
Fly forward until something gets in the way, in a field with one empty wall.

sim.launch.py with wall_world.sdf and no radio (the mission arms the drone), plus:
  sweep_view      distance ahead from the camera and the odometry
  forward_flight  takes off, flies forward, hovers when something is in the way
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, Shutdown
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue

WARN_M = 1.5    # m: sweep_view warns, and checks the way up to here; stop_m must be less


def generate_launch_description():
    def arg(name, kind):
        return ParameterValue(LaunchConfiguration(name), value_type=kind)
    share = get_package_share_directory('drone_bringup')
    clock = {'use_sim_time': True}
    return LaunchDescription([
        DeclareLaunchArgument('world', default_value='wall_world.sdf',
                              description='World to fly in; the drone flies the way it faces'),
        DeclareLaunchArgument('camera', default_value='follow',
                              description="The Gazebo window's view: free, follow or fpv"),
        DeclareLaunchArgument('headless', default_value='false',
                              description='true: no windows'),
        DeclareLaunchArgument('show', default_value='true',
                              description='Show what sweep_view sees in a window'),
        DeclareLaunchArgument('speed', default_value='0.4', description='m/s'),
        DeclareLaunchArgument('stop_m', default_value='0.8',
                              description='m: stop for anything nearer than this; the drone '
                                          'ends up closer, as stopping takes 0.2 m at 0.4 m/s'),
        DeclareLaunchArgument('max_distance', default_value='20.0',
                              description='m: stop here if nothing was in the way'),
        DeclareLaunchArgument('land', default_value='false',
                              description='true: land after stopping, false: hover'),
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(share, 'launch', 'sim.launch.py')),
            launch_arguments={
                'world': LaunchConfiguration('world'), 'camera': LaunchConfiguration('camera'),
                'headless': LaunchConfiguration('headless'), 'source': 'mission',
                'radio': 'false', 'demo': 'false'}.items()),
        Node(package='drone_sim', executable='sweep_view', output='screen',
             parameters=[clock, {'warn_m': WARN_M, 'show': arg('show', bool)}]),
        # Without it nothing would cancel the Goto: if it dies, everything stops.
        Node(package='drone_mission', executable='forward_flight', output='screen',
             parameters=[clock, {'stop_m': arg('stop_m', float), 'speed': arg('speed', float),
                                 'max_distance': arg('max_distance', float),
                                 'land': arg('land', bool)}],
             on_exit=Shutdown(reason='forward_flight ended')),
    ])
