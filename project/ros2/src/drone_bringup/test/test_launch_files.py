"""
Check what sim.launch.py starts for each combination of arguments, without starting it.

sim.launch.py decides everything in one function, setup(), once the arguments
are known. These tests call it the way ros2 launch would, but the Node and Gazebo
include it creates only record what they were given: which program,
which parameters, which remaps, and what goes to Gazebo. Nothing runs, so this
takes about a second and needs no Gazebo.

CI installs no Gazebo, ros_gz or joy (it installs build and test dependencies
only), so for those three packages a made-up install path is used, and their
programs are checked only where they are installed (the dev container).

Catches: a renamed program or package, a parameter file that is not installed,
a node that starts without sim.yaml, the inav backend starting Gazebo or the
radio nodes, a node on wall time in the sim (or sim time on the real drone),
a source publishing on the wrong topic, a launch argument renamed (ros2 launch
silently ignores unknown names, so the tests here refuse them), and a package
the launch needs but does not check for before starting Gazebo.
"""

import importlib.util
import itertools
import os
from pathlib import Path
from xml.etree import ElementTree

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchContext
from launch.actions import (DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription,
                            OpaqueFunction)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.utilities import perform_substitutions
from launch_ros.actions import Node
import pytest

PACKAGE_DIR = Path(__file__).resolve().parents[1]
LAUNCH_FILE = PACKAGE_DIR / 'launch' / 'sim.launch.py'
# Runtime-only packages that CI does not install.
NOT_IN_CI = {'ros_gz_sim', 'ros_gz_bridge', 'joy', 'image_transport',
             'compressed_image_transport'}


# ---------- running setup() without starting anything ----------

class RecordedNode(Node):
    """A real launch_ros Node (a misspelled keyword still fails) that keeps its arguments."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.recorded = kwargs


class RecordedSource(PythonLaunchDescriptionSource):
    """Keeps the path of the included launch file."""

    def __init__(self, path):
        super().__init__(path)
        self.path = path


class RecordedInclude(IncludeLaunchDescription):
    """Keeps the arguments passed to the included launch file (Gazebo's)."""

    def __init__(self, source, launch_arguments=None, **kwargs):
        self.recorded = dict(launch_arguments or {})
        super().__init__(source, launch_arguments=self.recorded.items(), **kwargs)
        self.path = source.path


def load_launch_file():
    spec = importlib.util.spec_from_file_location('sim_launch', LAUNCH_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def declared_arguments():
    """Return {name: DeclareLaunchArgument} of sim.launch.py."""
    entities = load_launch_file().generate_launch_description().entities
    return {e.name: e for e in entities if isinstance(e, DeclareLaunchArgument)}


def launch(*, gz_running=(), missing=(), **arguments):
    """
    Return what sim.launch.py would start with these arguments.

    gz_running: PIDs the Gazebo guard should find. missing: packages to pretend
    are not installed. Unknown names and values outside an argument's choices
    raise, as ros2 launch does for choices (but not for names).
    """
    module = load_launch_file()
    module.Node = RecordedNode
    module.IncludeLaunchDescription = RecordedInclude
    module.PythonLaunchDescriptionSource = RecordedSource
    module.gz_servers_in_my_partition = lambda: list(gz_running)

    def share(package):
        if package in missing:
            raise LookupError(package)
        try:
            return get_package_share_directory(package)
        except LookupError:
            if package in NOT_IN_CI:
                return f'/not-installed/{package}/share'
            raise
    module.get_package_share_directory = share

    entities = module.generate_launch_description().entities
    declared = {e.name: e for e in entities if isinstance(e, DeclareLaunchArgument)}
    (setup,) = [e for e in entities if isinstance(e, OpaqueFunction)]
    unknown = set(arguments) - set(declared)
    assert not unknown, f'sim.launch.py has no argument {sorted(unknown)}'
    context = LaunchContext()
    for name, decl in declared.items():
        value = arguments.get(name, perform_substitutions(context, decl.default_value))
        if decl.choices is not None:
            assert value in decl.choices, f'{name}:={value} is not one of {decl.choices}'
        context.launch_configurations[name] = value
    return setup.execute(context)


def every_combination():
    """Return every valid combination of the arguments that have a fixed set of choices."""
    choices = {name: d.choices for name, d in declared_arguments().items() if d.choices}
    every = [dict(zip(choices, values)) for values in itertools.product(*choices.values())]
    # Splitting over two machines is for the sim (test_split_is_for_the_sim_only).
    return [a for a in every if a['backend'] == 'sim' or a['part'] == 'all']


COMBINATIONS = every_combination()


def name_of(arguments):
    return ' '.join(f'{k}:={v}' for k, v in arguments.items())


def started(actions):
    """Return {executable: arguments given to Node} of every node."""
    nodes = {}
    for action in actions:
        if isinstance(action, RecordedNode):
            nodes[action.recorded['executable']] = action.recorded
    return nodes


def gazebo(actions):
    return [a for a in actions if isinstance(a, RecordedInclude)]


def files(node):
    """Return the parameter files given to a node."""
    return [p for p in node.get('parameters', []) if isinstance(p, str)]


def values(node):
    """Return the parameters given directly to a node, merged in order."""
    merged = {}
    for p in node.get('parameters', []):
        if isinstance(p, dict):
            merged.update(p)
    return merged


def remaps(node):
    return dict(node.get('remappings', []))


# ---------- which nodes start ----------

def test_default_is_the_sim_with_the_radio_and_the_mission():
    actions = launch()
    assert set(started(actions)) == {
        'parameter_bridge', 'flow_model', 'estimator', 'fc_bridge', 'watchdog',
        'safety_manager', 'metrics_exporter', 'mission', 'joy_node', 'radio_teleop'}
    assert len(gazebo(actions)) == 2      # server and window


def test_inav_backend_starts_no_gazebo_and_no_radio_nodes():
    # On the real drone the radio talks ELRS to INAV, and there is nothing to simulate.
    actions = launch(backend='inav', radio='true')
    assert gazebo(actions) == []
    assert set(started(actions)) == {'fc_bridge', 'watchdog', 'safety_manager',
                                     'metrics_exporter', 'mission'}
    assert values(started(actions)['fc_bridge'])['backend'] == 'inav'


def test_with_the_radio_only_the_radio_arms():
    for backend in ('sim', 'inav'):
        nodes = started(launch(backend=backend, radio='true'))
        assert values(nodes['fc_bridge'])['armed_at_start'] is False, backend
        assert values(nodes['mission'])['radio_arms'] is True, backend


def test_without_the_radio_the_mission_arms():
    nodes = started(launch(radio='false'))
    assert 'joy_node' not in nodes and 'radio_teleop' not in nodes
    assert values(nodes['fc_bridge'])['armed_at_start'] is True
    assert values(nodes['mission'])['radio_arms'] is False


def test_demo_flight_only_with_demo():
    assert 'demo_flight' in started(launch(source='mission', demo='true'))
    assert 'demo_flight' not in started(launch(source='mission', demo='false'))


@pytest.mark.parametrize('arguments', [
    {'source': 'none', 'demo': 'false'},
    {'source': 'none', 'demo': 'true'},
], ids=name_of)
def test_nothing_flies_without_a_source(arguments):
    nodes = set(started(launch(**arguments)))
    assert not nodes & {'mission', 'demo_flight'}
    assert {'fc_bridge', 'safety_manager'} <= nodes


# ---------- what goes to Gazebo ----------

def test_gazebo_server_and_window_are_two_processes():
    # One process with both deadlocks once the world has a camera (llvmpipe).
    server, window = gazebo(launch(world='some_world.sdf'))
    assert server.recorded['gz_args'] == '-s -r some_world.sdf'
    assert window.recorded['gz_args'] == '-g'
    assert window.recorded['on_exit_shutdown'] == 'true'   # closing it ends the launch
    for gz in (server, window):
        assert gz.path.endswith(os.path.join('launch', 'gz_sim.launch.py'))


def test_headless_starts_the_server_only():
    (gz,) = gazebo(launch(world='some_world.sdf', headless='true'))
    assert gz.recorded['gz_args'] == '-s -r some_world.sdf'


def test_camera_picks_the_window_view():
    for camera in ('free', 'follow', 'fpv'):
        actions = launch(camera=camera)
        _, window = gazebo(actions)
        follows = [a for a in actions if type(a) is ExecuteProcess]   # not a Node
        if camera == 'free':
            assert window.recorded['gz_args'] == '-g'     # Gazebo's own view
        else:
            option, config = window.recorded['gz_args'].split()[1:]
            assert option == '--gui-config' and os.path.isfile(config), config
            assert config.endswith(os.path.join('gui', camera + '.config'))
        # Only follow asks the window to follow the drone once it is up.
        assert len(follows) == (camera == 'follow'), camera
    assert not [a for a in launch(camera='follow', headless='true')
                if type(a) is ExecuteProcess]


# ---------- how the nodes are wired ----------

def test_each_source_publishes_on_its_own_topic():
    # safety_manager picks one of them and is the only publisher to fc_bridge.
    nodes = started(launch(source='mission', radio='true'))
    assert remaps(nodes['mission']) == {'setpoint_velocity': '/cmd/mission'}
    assert remaps(nodes['radio_teleop']) == {'setpoint_velocity': '/cmd/radio'}
    assert remaps(nodes['safety_manager']) == {}


def test_watchdog_always_watches_what_fc_bridge_gets():
    # Mandatory with every backend and source: it checks the link into fc_bridge.
    # Split, it runs on the station, beside safety_manager whose output it watches.
    for arguments in COMBINATIONS:
        nodes = started(launch(**arguments))
        if arguments['part'] == 'drone':
            assert 'watchdog' not in nodes, name_of(arguments)
            continue
        assert 'watchdog' in nodes, name_of(arguments)
        assert remaps(nodes['watchdog']) == {'setpoint_velocity': '/fc/setpoint_velocity'}


def test_sim_time_only_in_the_sim():
    wrong = []
    for arguments in COMBINATIONS:
        sim = arguments['backend'] == 'sim'
        for executable, node in started(launch(**arguments)).items():
            if executable in ('parameter_bridge', 'joy_node'):
                continue      # not ours: the bridge publishes /clock, joy stamps wall time
            if values(node).get('use_sim_time') is not sim:
                wrong.append(f'{name_of(arguments)}: {executable}')
    assert not wrong, 'use_sim_time must be true in the sim only:\n' + '\n'.join(wrong)


def test_every_node_reads_sim_yaml():
    sim_yaml = os.path.join(get_package_share_directory('drone_bringup'), 'config', 'sim.yaml')
    wrong = []
    for arguments in COMBINATIONS:
        for executable, node in started(launch(**arguments)).items():
            if executable != 'parameter_bridge' and sim_yaml not in files(node):
                wrong.append(f'{name_of(arguments)}: {executable}')   # bridge: gz_bridge.yaml
    assert not wrong, 'started without sim.yaml (so on code defaults):\n' + '\n'.join(wrong)


# ---------- everything it names exists ----------

def programs_in_every_combination():
    return sorted({(n['package'], n['executable'])
                   for arguments in COMBINATIONS
                   for n in started(launch(**arguments)).values()})


def program_path(package, executable):
    return os.path.join(get_package_prefix(package), 'lib', package, executable)


def test_our_programs_are_installed():
    ours = [(p, e) for p, e in programs_in_every_combination() if p not in NOT_IN_CI]
    missing = [f'{p} {e}' for p, e in ours if not os.access(program_path(p, e), os.X_OK)]
    assert not missing, f'not installed: {missing}'


def test_other_programs_are_installed():
    others = [(p, e) for p, e in programs_in_every_combination() if p in NOT_IN_CI]
    here = []
    for package, executable in others:
        try:
            here.append(program_path(package, executable))
        except LookupError:
            pass
    if not here:
        pytest.skip('ros_gz_bridge and joy are not installed here (CI); '
                    'the dev container checks them')
    assert all(os.access(p, os.X_OK) for p in here), here


def test_parameter_files_are_installed():
    missing = set()
    for arguments in COMBINATIONS:
        for executable, node in started(launch(**arguments)).items():
            for path in files(node) + [v for k, v in values(node).items() if k == 'config_file']:
                if not os.path.isfile(path):
                    missing.add(f'{executable}: {path}')
    assert not missing, 'parameter files that do not exist:\n' + '\n'.join(sorted(missing))


def test_every_package_it_starts_is_a_dependency():
    # Otherwise rosdep does not install it, and a fresh machine cannot launch.
    root = ElementTree.parse(PACKAGE_DIR / 'package.xml').getroot()
    depends = {e.text for e in root if e.tag in ('exec_depend', 'depend')}
    packages = {p for p, _ in programs_in_every_combination()} | {'ros_gz_sim'}
    assert packages <= depends, f'not in package.xml: {sorted(packages - depends)}'


# ---------- the checks before anything starts ----------

def test_every_package_it_starts_is_checked_first():
    # A package found missing mid-launch left Gazebo running orphaned; the
    # second launch then ran two sims in one partition. setup() checks
    # needed_packages() first, so it must cover all.
    module = load_launch_file()
    for arguments in COMBINATIONS:
        sim = arguments['backend'] == 'sim'
        actions = launch(**arguments)
        checked = set(module.needed_packages(sim, arguments['part']))
        used = {n['package'] for n in started(actions).values()}
        if gazebo(actions):
            used.add('ros_gz_sim')
        assert used <= checked, f'{name_of(arguments)}: unchecked {sorted(used - checked)}'


@pytest.mark.parametrize('package', ['drone_mission', 'drone_fc_bridge', 'ros_gz_bridge', 'joy'])
def test_a_missing_package_stops_the_launch(package):
    with pytest.raises(RuntimeError, match=package):
        launch(missing=[package])


def test_the_real_drone_needs_none_of_the_sim_packages():
    nodes = started(launch(backend='inav', missing=['ros_gz_sim', 'ros_gz_bridge', 'joy',
                                                    'drone_sim', 'drone_teleop']))
    assert 'fc_bridge' in nodes


def test_refuses_to_start_next_to_a_running_sim():
    with pytest.raises(RuntimeError, match='already running'):
        launch(gz_running=['4242'])
    assert started(launch(backend='inav', gz_running=['4242']))   # no Gazebo needed


# ---------- split over two machines: part:=drone on the laptop, part:=station on the Pi ----------

SIM_COMBINATIONS = [a for a in COMBINATIONS if a['backend'] == 'sim' and a['part'] == 'all']


def test_split_is_for_the_sim_only():
    # With the real drone there is nothing to play the drone: it all runs on the station.
    for part in ('drone', 'station'):
        with pytest.raises(RuntimeError, match='split the sim'):
            launch(backend='inav', part=part)


def test_drone_and_station_together_start_what_one_machine_does():
    # Each node runs on one machine only: two fc_bridges or two missions would fight.
    for arguments in SIM_COMBINATIONS:
        whole = set(started(launch(**arguments)))
        drone = set(started(launch(**dict(arguments, part='drone'))))
        station = set(started(launch(**dict(arguments, part='station'))))
        assert drone & station == {'republish'}, name_of(arguments)   # the camera link
        assert (drone | station) - {'republish'} == whole, name_of(arguments)


def test_the_drone_plays_the_drone_and_the_station_flies_it():
    drone = started(launch(part='drone', radio='true'))
    station = started(launch(part='station', radio='true'))
    assert {'fc_bridge', 'parameter_bridge', 'flow_model', 'estimator',
            'joy_node', 'radio_teleop'} <= set(drone)      # the radio is plugged into the laptop
    assert {'safety_manager', 'watchdog', 'mission', 'metrics_exporter'} <= set(station)
    assert not set(drone) & {'safety_manager', 'mission'}
    assert not set(station) & {'fc_bridge', 'parameter_bridge', 'joy_node'}


def test_both_halves_agree_on_who_arms():
    # The launch cannot check the other machine: both get radio:=, and it must match.
    for radio in ('true', 'false'):
        fc_bridge = started(launch(part='drone', radio=radio))['fc_bridge']
        mission = started(launch(part='station', radio=radio))['mission']
        assert values(fc_bridge)['armed_at_start'] is not values(mission)['radio_arms'], radio


def test_only_the_drone_starts_gazebo():
    assert len(gazebo(launch(part='drone'))) == 2
    assert gazebo(launch(part='station')) == []


def test_the_camera_crosses_the_network_compressed():
    module = load_launch_file()
    send = started(launch(part='drone'))['republish']
    receive = started(launch(part='station'))['republish']
    assert values(send)['in_transport'] == 'raw'
    assert values(send)['out_transport'] == 'compressed'
    assert remaps(send) == {'in': '/camera/image', 'out/compressed': module.LINK_IMAGE}
    assert values(receive)['in_transport'] == 'compressed'
    assert values(receive)['out_transport'] == 'raw'
    assert remaps(receive) == {'in/compressed': module.LINK_IMAGE, 'out': module.STATION_IMAGE}
    # One machine needs no link: nothing crosses a network.
    assert 'republish' not in started(launch())


def test_the_station_needs_none_of_the_gazebo_packages():
    # The Pi runs no Gazebo, and may not even have it installed.
    nodes = started(launch(part='station', missing=['ros_gz_sim', 'ros_gz_bridge', 'joy',
                                                    'drone_sim', 'drone_teleop']))
    assert 'mission' in nodes


def test_the_station_starts_next_to_a_running_sim():
    # On one machine for a test, the laptop runs both halves.
    assert started(launch(part='station', gz_running=['4242']))
    with pytest.raises(RuntimeError, match='already running'):
        launch(part='drone', gz_running=['4242'])


# ---------- wall_mission.launch.py: the forward flight on top of sim.launch.py ----------

WALL_FILE = PACKAGE_DIR / 'launch' / 'wall_mission.launch.py'


def wall_mission(env_display='', **arguments):
    """Return (arguments given to sim.launch.py, {executable: Node arguments})."""
    spec = importlib.util.spec_from_file_location('wall_launch', WALL_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.Node = RecordedNode
    module.IncludeLaunchDescription = RecordedInclude
    module.PythonLaunchDescriptionSource = RecordedSource
    entities = module.generate_launch_description().entities
    declared = {e.name: e for e in entities if isinstance(e, DeclareLaunchArgument)}
    (setup,) = [e for e in entities if isinstance(e, OpaqueFunction)]
    unknown = set(arguments) - set(declared)
    assert not unknown, f'wall_mission.launch.py has no argument {sorted(unknown)}'
    context = LaunchContext()
    for name, decl in declared.items():
        context.launch_configurations[name] = arguments.get(
            name, perform_substitutions(context, decl.default_value))
    old = os.environ.get('DISPLAY')
    os.environ['DISPLAY'] = env_display
    try:
        actions = setup.execute(context)
    finally:
        if old is None:
            del os.environ['DISPLAY']
        else:
            os.environ['DISPLAY'] = old
    (include,) = [a for a in actions if isinstance(a, RecordedInclude)]
    return include.recorded, started(actions)


def test_wall_mission_passes_the_part_to_the_sim():
    for part in ('all', 'drone', 'station'):
        sim_arguments, _ = wall_mission(part=part)
        assert sim_arguments['part'] == part
        assert sim_arguments['radio'] == 'false'      # both halves: the mission arms
        assert set(sim_arguments) <= set(declared_arguments())


def test_wall_mission_flies_from_the_station():
    _, nodes = wall_mission(part='drone')
    assert not set(nodes) & {'sweep_view', 'forward_flight'}
    for part in ('all', 'station'):
        _, nodes = wall_mission(part=part)
        assert {'sweep_view', 'forward_flight'} <= set(nodes), part


def test_wall_mission_station_reads_the_unpacked_camera():
    sim = load_launch_file()
    _, nodes = wall_mission(part='station')
    assert remaps(nodes['sweep_view']) == {'camera/image': sim.STATION_IMAGE}
    _, nodes = wall_mission(part='all')
    assert remaps(nodes['sweep_view']) == {}           # one machine: Gazebo's camera directly


def test_wall_mission_window_only_with_a_screen():
    def show(display, value):
        _, nodes = wall_mission(env_display=display, show=value)
        return values(nodes['sweep_view'])['show']
    assert show('', 'auto') is False                   # the Pi over SSH
    assert show(':0', 'auto') is True
    assert show('', 'true') is True and show(':0', 'false') is False
