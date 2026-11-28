"""
Fly forward until something gets in the way, in a field with one empty wall.

sim.launch.py with wall_world.sdf and no radio (the mission arms the drone), plus:
  sweep_view      distance ahead from the camera and the odometry
  forward_flight  takes off, flies forward, hovers when something is in the way

part:= splits it over two machines on ROS_DOMAIN_ID 6, as sim.launch.py does:
  drone    on the laptop: Gazebo and what plays the drone (make sim-wall-drone)
  station  on the ground station (the Pi 5): the mission, sweep_view and
           forward_flight, on the camera that crosses the network as JPEG
           (make sim-wall-station)
"""
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction,
                            Shutdown)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

WARN_M = 1.5    # m: sweep_view warns, and checks the way up to here; stop_m must be less
STATION_IMAGE = '/station/camera/image'   # sim.launch.py's, where the station unpacks the camera


def setup(context):
    def arg(name):
        return LaunchConfiguration(name).perform(context)
    share = get_package_share_directory('drone_bringup')
    part = arg('part')
    actions = [IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(share, 'launch', 'sim.launch.py')),
        launch_arguments={
            'world': arg('world'), 'camera': arg('camera'), 'headless': arg('headless'),
            'source': 'mission', 'radio': 'false', 'demo': 'false', 'part': part}.items())]
    if part == 'drone':
        return actions
    clock = {'use_sim_time': True}
    # auto: a window only where there is a screen (the Pi runs without a desktop,
    # and imshow without one would end sweep_view).
    show = arg('show') == 'true' or (arg('show') == 'auto' and bool(os.environ.get('DISPLAY')))
    camera = [('camera/image', STATION_IMAGE)] if part == 'station' else []
    actions.append(Node(package='drone_sim', executable='sweep_view', output='screen',
                        remappings=camera,
                        parameters=[clock, {'warn_m': WARN_M, 'show': show}]))
    # Without it nothing would cancel the Goto: if it dies, everything stops (split:
    # the station does, and fc_bridge on the laptop gets no setpoints and holds).
    actions.append(Node(
        package='drone_mission', executable='forward_flight', output='screen',
        parameters=[clock, {'stop_m': float(arg('stop_m')), 'speed': float(arg('speed')),
                            'max_distance': float(arg('max_distance')),
                            'land': arg('land') == 'true'}],
        on_exit=Shutdown(reason='forward_flight ended')))
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('world', default_value='wall_world.sdf',
                              description='World to fly in; the drone flies the way it faces'),
        DeclareLaunchArgument('camera', default_value='follow',
                              description="The Gazebo window's view: free, follow or fpv"),
        DeclareLaunchArgument('headless', default_value='false',
                              description='true: no Gazebo window'),
        DeclareLaunchArgument('show', default_value='auto', choices=['auto', 'true', 'false'],
                              description="sweep_view's window. auto: only with a screen"),
        DeclareLaunchArgument('speed', default_value='0.4', description='m/s'),
        DeclareLaunchArgument('stop_m', default_value='0.8',
                              description='m: stop for anything nearer than this; the drone '
                                          'ends up closer, as stopping takes 0.2 m at 0.4 m/s'),
        DeclareLaunchArgument('max_distance', default_value='20.0',
                              description='m: stop here if nothing was in the way'),
        DeclareLaunchArgument('land', default_value='false',
                              description='true: land after stopping, false: hover'),
        DeclareLaunchArgument('part', default_value='all', choices=['all', 'drone', 'station'],
                              description='all: one machine. drone: the laptop with Gazebo. '
                                          'station: the ground station (mission, sweep_view)'),
        OpaqueFunction(function=setup),
    ])
