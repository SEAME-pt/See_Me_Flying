import os
import subprocess

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (EqualsSubstitution, LaunchConfiguration, PathJoinSubstitution,
                                  PythonExpression)
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare

SIM = {'use_sim_time': True}
# Every source publishes on its own topic; safety_manager picks one for fc_bridge.
TO_MISSION = [('setpoint_velocity', '/cmd/mission')]
TO_RADIO = [('setpoint_velocity', '/cmd/radio')]


PACKAGES = ['ros_gz_sim', 'ros_gz_bridge', 'drone_fc_bridge', 'drone_safety', 'drone_mission',
            'drone_basics_py', 'joy']


def is_source(name):
    return IfCondition(EqualsSubstitution(LaunchConfiguration('source'), name))


def gz_servers_in_my_partition():
    """Return the PIDs of Gazebo processes already running in this shell's GZ_PARTITION."""
    mine = os.environ.get('GZ_PARTITION', '')
    # 'gz sim ...', 'gz sim server', 'gz sim gui'; with -s there is no separate server.
    found = subprocess.run(['pgrep', '-f', '^gz sim'], capture_output=True, text=True)
    pids = []
    for pid in found.stdout.split():
        try:
            with open(f'/proc/{pid}/environ', 'rb') as f:
                env = dict(v.split(b'=', 1) for v in f.read().split(b'\0') if b'=' in v)
        except OSError:
            continue   # exited meanwhile, or not ours to read
        if env.get(b'GZ_PARTITION', b'').decode() == mine:
            pids.append(pid)
    return pids


def check_before_starting():
    # Both run before any process starts. A missing package found later, mid-launch,
    # used to leave the already-started Gazebo orphaned; a second launch then ran
    # two sims in one partition and fc_bridge read both drones in turn (flicker).
    for package in PACKAGES:
        try:
            get_package_share_directory(package)
        except LookupError:
            raise RuntimeError(f"Package '{package}' not found: run colcon build, then "
                               'source install/setup.bash in this terminal') from None
    running = gz_servers_in_my_partition()
    if running:
        raise RuntimeError(f'Gazebo is already running (PID {", ".join(running)}): two sims '
                           'would share topics. Stop it first: pkill -f "gz sim"')


def generate_launch_description():
    check_before_starting()
    bringup = FindPackageShare('drone_bringup')
    params = PathJoinSubstitution([bringup, 'config', 'sim.yaml'])
    bridge_cfg = PathJoinSubstitution([bringup, 'config', 'gz_bridge.yaml'])

    args = [
        DeclareLaunchArgument('source', default_value='circle',
                              choices=['circle', 'mission', 'none'],
                              description='What flies the drone on its own; the radio is '
                                          'always there and overrides it'),
        DeclareLaunchArgument('demo', default_value='true', choices=['true', 'false'],
                              description='With source:=mission, also run demo_flight'),
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

    # The only publisher of /fc/setpoint_velocity: radio > manual > mission.
    safety = Node(
        package='drone_safety', executable='safety_manager',
        parameters=[params, SIM], output='screen',
    )

    # source:=circle — takeoff then circles, 5 s after the rest (as today)
    circle = TimerAction(period=5.0, condition=is_source('circle'), actions=[Node(
        package='drone_basics_py', executable='setpoint_pub',
        remappings=TO_MISSION, parameters=[params, SIM], output='screen',
    )])

    # source:=mission — Takeoff, Goto and Land action servers on the rangefinder,
    # and (demo:=true) demo_flight: takeoff, a square, land. No delay needed:
    # demo_flight retries Takeoff until the rangefinder is up.
    mission = Node(
        package='drone_mission', executable='mission',
        remappings=TO_MISSION, parameters=[params, SIM], output='screen',
        condition=is_source('mission'),
    )
    demo = Node(
        package='drone_mission', executable='demo_flight',
        parameters=[params, SIM], output='screen',
        condition=IfCondition(PythonExpression([
            "'", LaunchConfiguration('source'), "' == 'mission' and '",
            LaunchConfiguration('demo'), "' == 'true'"])),
    )

    # Always: the RadioMaster Pocket over USB, like the real drone, which never flies
    # without the radio as a backup. Engaged (arm switch on), it overrides any source.
    # Not plugged in: joy_node waits quietly and picks it up when it appears.
    joy = Node(
        package='joy', executable='joy_node',
        parameters=[params], output='screen',
    )
    radio = Node(
        package='drone_basics_py', executable='radio_teleop',
        remappings=TO_RADIO, parameters=[params, SIM], output='screen',
    )

    return LaunchDescription(args + [gazebo, bridge, fc_bridge, safety, circle, mission, demo,
                                     joy, radio])
