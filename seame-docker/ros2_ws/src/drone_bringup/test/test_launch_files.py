"""
Check what sim.launch.py starts for each combination of arguments, without starting it.

sim.launch.py decides everything in one function, setup(), once the arguments
are known. These tests call it the way ros2 launch would, but the Node, Gazebo
include and timer it creates only record what they were given: which program,
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
from launch.actions import (DeclareLaunchArgument, IncludeLaunchDescription, OpaqueFunction,
                            TimerAction)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.utilities import perform_substitutions
from launch_ros.actions import Node
import pytest

PACKAGE_DIR = Path(__file__).resolve().parents[1]
LAUNCH_FILE = PACKAGE_DIR / 'launch' / 'sim.launch.py'
# Runtime-only packages that CI does not install.
NOT_IN_CI = {'ros_gz_sim', 'ros_gz_bridge', 'joy'}


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


class RecordedTimer(TimerAction):
    """Keeps the delay and the actions it starts."""

    def __init__(self, *, period, actions, **kwargs):
        super().__init__(period=period, actions=actions, **kwargs)
        self.delay_s = period
        self.inner = list(actions)


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
    module.TimerAction = RecordedTimer
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
    """Return every combination of the arguments that have a fixed set of choices."""
    choices = {name: d.choices for name, d in declared_arguments().items() if d.choices}
    return [dict(zip(choices, values)) for values in itertools.product(*choices.values())]


COMBINATIONS = every_combination()


def name_of(arguments):
    return ' '.join(f'{k}:={v}' for k, v in arguments.items())


def started(actions):
    """Return {executable: arguments given to Node} of every node, timed ones included."""
    nodes = {}
    for action in actions:
        if isinstance(action, RecordedTimer):
            nodes.update(started(action.inner))
        elif isinstance(action, RecordedNode):
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
        'parameter_bridge', 'flow_model', 'fc_bridge', 'safety_manager', 'mission',
        'joy_node', 'radio_teleop'}
    assert len(gazebo(actions)) == 1


def test_inav_backend_starts_no_gazebo_and_no_radio_nodes():
    # On the real drone the radio talks ELRS to INAV, and there is nothing to simulate.
    actions = launch(backend='inav', radio='true')
    assert gazebo(actions) == []
    assert set(started(actions)) == {'fc_bridge', 'safety_manager', 'mission'}
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


def test_circle_demo_starts_setpoint_pub_after_the_rest():
    actions = launch(source='circle', demo='true')
    nodes = started(actions)
    assert 'setpoint_pub' in nodes and 'mission' not in nodes
    (timer,) = [a for a in actions if isinstance(a, RecordedTimer)]
    assert timer.delay_s > 0
    assert [n.recorded['executable'] for n in timer.inner] == ['setpoint_pub']


@pytest.mark.parametrize('arguments', [
    {'source': 'circle', 'demo': 'false'},
    {'source': 'none', 'demo': 'false'},
    {'source': 'none', 'demo': 'true'},
], ids=name_of)
def test_nothing_flies_without_a_source(arguments):
    nodes = set(started(launch(**arguments)))
    assert not nodes & {'mission', 'demo_flight', 'setpoint_pub'}
    assert {'fc_bridge', 'safety_manager'} <= nodes


# ---------- what goes to Gazebo ----------

def test_gazebo_gets_the_world_and_headless_adds_server_only():
    (gz,) = gazebo(launch(world='some_world.sdf'))
    assert gz.recorded['gz_args'] == '-r some_world.sdf'
    (gz,) = gazebo(launch(world='some_world.sdf', headless='true'))
    assert gz.recorded['gz_args'] == '-s -r some_world.sdf'
    assert gz.path.endswith(os.path.join('launch', 'gz_sim.launch.py'))


# ---------- how the nodes are wired ----------

def test_each_source_publishes_on_its_own_topic():
    # safety_manager picks one of them and is the only publisher to fc_bridge.
    nodes = started(launch(source='mission', radio='true'))
    assert remaps(nodes['mission']) == {'setpoint_velocity': '/cmd/mission'}
    assert remaps(nodes['radio_teleop']) == {'setpoint_velocity': '/cmd/radio'}
    assert remaps(nodes['safety_manager']) == {}
    nodes = started(launch(source='circle', demo='true'))
    assert remaps(nodes['setpoint_pub']) == {'setpoint_velocity': '/cmd/mission'}


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
    # PACKAGES (sim) or REAL_PACKAGES (inav) first, so they must cover all.
    module = load_launch_file()
    for arguments in COMBINATIONS:
        sim = arguments['backend'] == 'sim'
        checked = set(module.PACKAGES if sim else module.REAL_PACKAGES)
        used = {n['package'] for n in started(launch(**arguments)).values()}
        if sim:
            used.add('ros_gz_sim')
        assert used <= checked, f'{name_of(arguments)}: unchecked {sorted(used - checked)}'


@pytest.mark.parametrize('package', ['drone_mission', 'drone_fc_bridge', 'ros_gz_bridge', 'joy'])
def test_a_missing_package_stops_the_launch(package):
    with pytest.raises(RuntimeError, match=package):
        launch(missing=[package])


def test_the_real_drone_needs_none_of_the_sim_packages():
    nodes = started(launch(backend='inav', missing=['ros_gz_sim', 'ros_gz_bridge', 'joy',
                                                    'drone_sim_sensors']))
    assert 'fc_bridge' in nodes


def test_refuses_to_start_next_to_a_running_sim():
    with pytest.raises(RuntimeError, match='already running'):
        launch(gz_running=['4242'])
    assert started(launch(backend='inav', gz_running=['4242']))   # no Gazebo needed
