import os
import subprocess

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    AppendEnvironmentVariable,
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    OpaqueFunction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# Every source publishes on its own topic; safety_manager picks one for fc_bridge.
TO_MISSION = [('setpoint_velocity', '/cmd/mission')]
TO_RADIO = [('setpoint_velocity', '/cmd/radio')]
# The watchdog listens to what fc_bridge gets: safety_manager's output.
TO_WATCHDOG = [('setpoint_velocity', '/fc/setpoint_velocity')]

PACKAGES = ['ros_gz_sim', 'ros_gz_bridge', 'drone_fc_bridge', 'drone_safety', 'drone_mission',
            'drone_monitoring', 'joy', 'drone_sim', 'drone_teleop']
REAL_PACKAGES = ['drone_fc_bridge', 'drone_safety', 'drone_mission', 'drone_monitoring']

# part:=drone and part:=station split the sim over two machines on ROS_DOMAIN_ID 6.
# drone (the laptop) plays the drone: Gazebo, the simulated sensors, fc_bridge and the
# radio. station (the ground station, the Pi 5) runs what it runs on the real drone:
# safety_manager, watchdog, mission and metrics. Raw, the camera is about 28 MB/s,
# too much for Wi-Fi: it crosses the network as JPEG (LINK_IMAGE, about 3 MB/s) and
# the station unpacks it to STATION_IMAGE. Nothing on the station may subscribe to
# camera/image itself: that would pull the raw images across the network.
CAMERA_LINK = ['image_transport', 'compressed_image_transport']
DRONE_PACKAGES = ['ros_gz_sim', 'ros_gz_bridge', 'drone_fc_bridge', 'drone_sim', 'joy',
                  'drone_teleop'] + CAMERA_LINK
STATION_PACKAGES = REAL_PACKAGES + CAMERA_LINK
LINK_IMAGE = '/link/camera/compressed'
STATION_IMAGE = '/station/camera/image'

# camera:=follow. The window loads before the drone is in its scene, so its config
# cannot start following (offset and smoothing do come from follow.config).
# Ask the window to follow x3 (the drone in every world) once it answers.
FOLLOW_DRONE = ('until gz service -s /gui/follow --reqtype gz.msgs.StringMsg '
                '--reptype gz.msgs.Boolean --timeout 1000 --req \'data: "x3"\' '
                '| grep -q true; do sleep 1; done')

# camera:=follow. The window loads before the drone is in its scene, so its config
# cannot start following (offset and smoothing do come from follow.config).
# Ask the window to follow x3 (the drone in every world) once it answers.
FOLLOW_DRONE = ('until gz service -s /gui/follow --reqtype gz.msgs.StringMsg '
                '--reptype gz.msgs.Boolean --timeout 1000 --req \'data: "x3"\' '
                '| grep -q true; do sleep 1; done')


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


def needed_packages(sim, part):
    """Return the packages a launch with these arguments starts programs from."""
    if not sim:
        return REAL_PACKAGES
    return {'all': PACKAGES, 'drone': DRONE_PACKAGES, 'station': STATION_PACKAGES}[part]


def check_before_starting(sim, part):
    # Both run before any process starts. A missing package found later, mid-launch,
    # used to leave the already-started Gazebo orphaned; a second launch then ran
    # two sims in one partition and fc_bridge read both drones in turn (flicker).
    for package in needed_packages(sim, part):
        try:
            get_package_share_directory(package)
        except LookupError:
            raise RuntimeError(f"Package '{package}' not found: run colcon build, then "
                               'source install/setup.bash in this terminal') from None
    # The station starts no Gazebo, so one running there (or none) is no matter.
    running = gz_servers_in_my_partition() if sim and part != 'station' else []
    if running:
        raise RuntimeError(f'Gazebo is already running (PID {", ".join(running)}): two sims '
                           'would share topics. Stop it first: pkill -f "gz sim"')


def setup(context):
    def arg(name):
        return LaunchConfiguration(name).perform(context)
    sim = arg('backend') == 'sim'
    radio = arg('radio') == 'true'
    source = arg('source')
    part = arg('part')
    if part != 'all' and not sim:
        raise RuntimeError('part:=drone and part:=station split the sim over two machines; '
                           'with backend:=inav everything runs on the ground station')
    check_before_starting(sim, part)
    drone = part in ('all', 'drone')       # plays the drone (sim) or talks to it (inav)
    station = part in ('all', 'station')   # what the ground station runs

    config = os.path.join(get_package_share_directory('drone_bringup'), 'config')
    params = os.path.join(config, 'sim.yaml')
    clock = {'use_sim_time': sim}
    # Like the real drone, only the radio arms. Without it (radio:=false, sim only),
    # fc_bridge starts armed and the mission arms on Takeoff and disarms after a Land.
    radio_arms = radio or not sim

    actions = []
    if sim and drone:
        share = get_package_share_directory('drone_bringup')
        # model://grass_ground, model://textured_floor, ... live in our package
        actions.append(AppendEnvironmentVariable(
            'GZ_SIM_RESOURCE_PATH', os.path.join(share, 'models')))
        # A bare name that exists in our worlds/ wins; otherwise pass it through
        # (full paths and Gazebo's own worlds, like multicopter_velocity_control.sdf)
        world = arg('world')
        ours = os.path.join(share, 'worlds', world)
        # The world's surfaces file, if it has one (worlds/<world>_surfaces.yaml):
        # flow quality then depends on the floor under the drone.
        stem = os.path.splitext(os.path.basename(world))[0]
        surfaces = os.path.join(share, 'worlds', stem + '_surfaces.yaml')
        surfaces = surfaces if os.path.exists(surfaces) else ''
        if os.path.isfile(ours):
            world = ours
        # The server (-s) and the window (-g) run as two processes. In one process
        # the window and the server's FPV camera rendering deadlock on software
        # rendering (llvmpipe, the dev container): Gazebo hangs and shows nothing.
        # headless:=true: server only, no window, for CI and the nightly flight tests.
        gz_sim = PythonLaunchDescriptionSource(os.path.join(
            get_package_share_directory('ros_gz_sim'), 'launch', 'gz_sim.launch.py'))
        actions.append(IncludeLaunchDescription(
            gz_sim, launch_arguments={'gz_args': '-s -r ' + world}.items(),
        ))
        if arg('headless') != 'true':
            # camera: the window's main view, from config/gui/<camera>.config;
            # free is Gazebo's own. Closing the window ends the launch.
            gui = '-g'
            if arg('camera') != 'free':
                gui += ' --gui-config ' + os.path.join(config, 'gui', arg('camera') + '.config')
            actions.append(IncludeLaunchDescription(
                gz_sim, launch_arguments={'gz_args': gui, 'on_exit_shutdown': 'true'}.items(),
            ))
            if arg('camera') == 'follow':
                actions.append(ExecuteProcess(cmd=['bash', '-c', FOLLOW_DRONE]))
        actions.append(Node(
            package='ros_gz_bridge', executable='parameter_bridge',
            parameters=[{'config_file': os.path.join(config, 'gz_bridge.yaml')}],
            output='screen',
        ))
        # Synthetic optical flow from ground truth; tuned in sim.yaml (flow_model).
        actions.append(Node(
            package='drone_sim', executable='flow_model',
            parameters=[params, clock, {'surfaces_file': surfaces}], output='screen',
        ))
        # Estimator v1: fc/odom from flow, range and attitude (drone_sim).
        actions.append(Node(
            package='drone_sim', executable='estimator',
            parameters=[params, clock], output='screen',
        ))

    if drone:
        # Split, the station's mission must see the same radio:=: it decides
        # whether the mission arms (radio_arms), and fc_bridge whether it starts armed.
        actions.append(Node(
            package='drone_fc_bridge', executable='fc_bridge', output='screen',
            parameters=[params, clock, {'backend': arg('backend'),
                                        'armed_at_start': not radio_arms}],
        ))
    if part == 'drone':
        # The camera to the station: JPEG instead of 28 MB/s raw (see LINK_IMAGE).
        actions.append(Node(
            package='image_transport', executable='republish', name='camera_link_send',
            output='screen', parameters=[params, clock, {
                'in_transport': 'raw', 'out_transport': 'compressed'}],
            remappings=[('in', '/camera/image'), ('out/compressed', LINK_IMAGE)],
        ))
    if part == 'station':
        # ...and back to a raw image on the station, stamps unchanged.
        actions.append(Node(
            package='image_transport', executable='republish', name='camera_link_receive',
            output='screen', parameters=[params, clock, {
                'in_transport': 'compressed', 'out_transport': 'raw'}],
            remappings=[('in/compressed', LINK_IMAGE), ('out', STATION_IMAGE)],
        ))
    if station:
        actions += station_nodes(source, arg('demo') == 'true', radio_arms, params, clock)
    if drone:
        actions += radio_nodes(sim and radio, params, clock)
    return actions


def station_nodes(source, demo, radio_arms, params, clock):
    """Return what the ground station runs: safety, watchdog, metrics and the mission."""
    nodes = [
        # Watches the setpoint stream into fc_bridge: warns when it stops for timeout_s
        # and when it comes back. Mandatory; only logs (fc_bridge's timeout sends zero).
        Node(package='drone_fc_bridge', executable='watchdog', output='screen',
             remappings=TO_WATCHDOG, parameters=[params, clock]),
        # The only publisher of /fc/setpoint_velocity: radio > manual > mission.
        Node(package='drone_safety', executable='safety_manager',
             parameters=[params, clock], output='screen'),
        # Prometheus metrics on localhost:9105 for the Grafana dashboard (make monitor).
        # Only listens; if it fails, the rest flies on.
        Node(package='drone_monitoring', executable='metrics_exporter',
             parameters=[params, clock], output='screen'),
    ]
    # demo:=true runs a scripted flight for the source; without it nothing flies
    # until someone sends a goal or takes the sticks.
    if source == 'mission':
        # Takeoff, Goto and Land action servers on the rangefinder, always; with
        # demo:=true also demo_flight: takeoff, a square, land. demo_flight retries
        # Takeoff until the rangefinder is up and the drone is armed.
        nodes.append(Node(package='drone_mission', executable='mission',
                          remappings=TO_MISSION, output='screen',
                          parameters=[params, clock, {'radio_arms': radio_arms}]))
        if demo:
            nodes.append(Node(package='drone_mission', executable='demo_flight',
                              parameters=[params, clock], output='screen'))
    return nodes


def radio_nodes(wanted, params, clock):
    """
    Return the RadioMaster Pocket over USB, playing the part INAV plays on the real drone.

    Arm switch arms, takeover switch overrides any source. Not plugged in: joy_node
    waits quietly and picks it up when it appears. On the real drone the radio talks
    ELRS to INAV, so neither node runs with backend:=inav; split, they run with the
    drone (the laptop the radio is plugged into).
    """
    if not wanted:
        return []
    return [
        Node(package='joy', executable='joy_node', parameters=[params], output='screen'),
        Node(package='drone_teleop', executable='radio_teleop',
             remappings=TO_RADIO, parameters=[params, clock], output='screen'),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument('backend', default_value='sim', choices=['sim', 'inav'],
                              description='sim: Gazebo. inav: the real drone over MSP '
                                          '(listen-only: reads state, sends no commands)'),
        DeclareLaunchArgument('source', default_value='mission',
                              choices=['mission', 'none'],
                              description='What commands the drone besides the radio: '
                                          'mission (action servers) or none'),
        DeclareLaunchArgument('radio', default_value='true', choices=['true', 'false'],
                              description='Sim only. false: no RadioMaster (someone else has '
                                          'it); the mission arms the drone itself'),
        DeclareLaunchArgument('demo', default_value='false', choices=['true', 'false'],
                              description='Fly a scripted demo with source:=mission: '
                                          'takeoff, a square, land'),
        DeclareLaunchArgument('world', default_value='room_world.sdf',
                              description='Sim only: SDF world file name or full path'),
        DeclareLaunchArgument('camera', default_value='free',
                              choices=['free', 'follow', 'fpv'],
                              description="Sim only: the Gazebo window's main view. free: "
                                          "Gazebo's own, follow: behind the drone, fpv: "
                                          "the drone's front camera (our worlds only)"),
        DeclareLaunchArgument('headless', default_value='false', choices=['true', 'false'],
                              description='Sim only. true: Gazebo without its window '
                                          '(server only), for CI and the nightly tests'),
        DeclareLaunchArgument('part', default_value='all', choices=['all', 'drone', 'station'],
                              description='Sim only. all: one machine. Split over two: '
                                          'drone (laptop: Gazebo, sensors, fc_bridge, radio) '
                                          'and station (ground station: safety, mission); '
                                          'give both the same radio:='),
        # Everything else is decided once the arguments are known, and checked
        # before any process starts.
        OpaqueFunction(function=setup),
    ])
