import os
import subprocess

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction,
                            TimerAction)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# Every source publishes on its own topic; safety_manager picks one for fc_bridge.
TO_MISSION = [('setpoint_velocity', '/cmd/mission')]
TO_RADIO = [('setpoint_velocity', '/cmd/radio')]

PACKAGES = ['ros_gz_sim', 'ros_gz_bridge', 'drone_fc_bridge', 'drone_safety', 'drone_mission',
            'drone_basics_py', 'joy']
REAL_PACKAGES = ['drone_fc_bridge', 'drone_safety', 'drone_mission', 'drone_basics_py']


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


def check_before_starting(sim):
    # Both run before any process starts. A missing package found later, mid-launch,
    # used to leave the already-started Gazebo orphaned; a second launch then ran
    # two sims in one partition and fc_bridge read both drones in turn (flicker).
    for package in PACKAGES if sim else REAL_PACKAGES:
        try:
            get_package_share_directory(package)
        except LookupError:
            raise RuntimeError(f"Package '{package}' not found: run colcon build, then "
                               'source install/setup.bash in this terminal') from None
    running = gz_servers_in_my_partition() if sim else []
    if running:
        raise RuntimeError(f'Gazebo is already running (PID {", ".join(running)}): two sims '
                           'would share topics. Stop it first: pkill -f "gz sim"')


def setup(context):
    def arg(name):
        return LaunchConfiguration(name).perform(context)
    sim = arg('backend') == 'sim'
    radio = arg('radio') == 'true'
    source = arg('source')
    check_before_starting(sim)

    config = os.path.join(get_package_share_directory('drone_bringup'), 'config')
    params = os.path.join(config, 'sim.yaml')
    clock = {'use_sim_time': sim}
    # Like the real drone, only the radio arms. Without it (radio:=false, sim only),
    # fc_bridge starts armed and the mission arms on Takeoff and disarms after a Land.
    radio_arms = radio or not sim

    actions = []
    if sim:
        actions.append(IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(
                get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py')),
            launch_arguments={'gz_args': '-r ' + arg('world')}.items(),
        ))
        actions.append(Node(
            package='ros_gz_bridge', executable='parameter_bridge',
            parameters=[{'config_file': os.path.join(config, 'gz_bridge.yaml')}],
            output='screen',
        ))

    actions.append(Node(
        package='drone_fc_bridge', executable='fc_bridge', output='screen',
        parameters=[params, clock, {'backend': arg('backend'),
                                    'armed_at_start': not radio_arms}],
    ))
    # The only publisher of /fc/setpoint_velocity: radio > manual > mission.
    actions.append(Node(
        package='drone_safety', executable='safety_manager',
        parameters=[params, clock], output='screen',
    ))

    if source == 'circle':
        # Takeoff then circles, 5 s after the rest. On a timer, not on arming:
        # with radio:=true, arm before it starts.
        actions.append(TimerAction(period=5.0, actions=[Node(
            package='drone_basics_py', executable='setpoint_pub',
            remappings=TO_MISSION, parameters=[params, clock], output='screen',
        )]))
    elif source == 'mission':
        # Takeoff, Goto and Land action servers on the rangefinder, and (demo:=true)
        # demo_flight: takeoff, a square, land. demo_flight retries Takeoff until
        # the rangefinder is up and the drone is armed.
        actions.append(Node(
            package='drone_mission', executable='mission',
            remappings=TO_MISSION, output='screen',
            parameters=[params, clock, {'radio_arms': radio_arms}],
        ))
        if arg('demo') == 'true':
            actions.append(Node(
                package='drone_mission', executable='demo_flight',
                parameters=[params, clock], output='screen',
            ))

    if sim and radio:
        # The RadioMaster Pocket over USB, playing the part INAV plays on the real
        # drone: arm switch arms, takeover switch overrides any source. Not plugged
        # in: joy_node waits quietly and picks it up when it appears. On the real
        # drone the radio talks ELRS to INAV, so neither node runs with backend:=inav.
        actions.append(Node(
            package='joy', executable='joy_node', parameters=[params], output='screen',
        ))
        actions.append(Node(
            package='drone_basics_py', executable='radio_teleop',
            remappings=TO_RADIO, parameters=[params, clock], output='screen',
        ))
    return actions


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('backend', default_value='sim', choices=['sim', 'inav'],
                              description='sim: Gazebo. inav: the real drone over MSP '
                                          '(stub: nothing sent yet)'),
        DeclareLaunchArgument('source', default_value='circle',
                              choices=['circle', 'mission', 'none'],
                              description='What flies the drone on its own; the radio '
                                          'overrides it'),
        DeclareLaunchArgument('radio', default_value='true', choices=['true', 'false'],
                              description='Sim only. false: no RadioMaster (someone else has '
                                          'it); the mission arms the drone itself'),
        DeclareLaunchArgument('demo', default_value='true', choices=['true', 'false'],
                              description='With source:=mission, also run demo_flight'),
        DeclareLaunchArgument('world', default_value='multicopter_velocity_control.sdf',
                              description='Sim only: SDF world file name or full path'),
        # Everything else is decided once the arguments are known, and checked
        # before any process starts.
        OpaqueFunction(function=setup),
    ])
