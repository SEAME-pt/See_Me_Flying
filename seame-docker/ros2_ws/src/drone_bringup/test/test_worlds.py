"""
Check the Gazebo worlds the sim can open: the drone is in each one, wired to our bridge.

Reads the .sdf files only; Gazebo is not started, so this takes about a second.

The worlds checked:
- every world in drone_bringup/worlds/ (outdoor_field.sdf comes with branch
  feature/153; before it there are none);
- sim.launch.py's default world, multicopter_velocity_control.sdf, which is
  Gazebo's own. CI installs no Gazebo, so there it is skipped; run_tests.sh in
  the dev container checks it.

In each world:
- the physics system is loaded (without it nothing moves);
- exactly one model has a velocity controller on the topics gz_bridge.yaml
  sends to (/X3/gazebo/command/twist and /X3/enable): that is the drone;
- the drone publishes odometry on the topic gz_bridge.yaml reads, which becomes
  /X3/odom for fc_bridge and /sim/ground_truth for the tests;
- the drone starts on the ground, as the mission and the flight test expect,
  and its Fuel model is pinned to a version;
- every model:// it uses exists.
Every model in drone_bringup/models/ has its .sdf and the textures and meshes
it names, and worlds and models are installed, or the launch can't find them.

Catches: a new world where the drone ignores our commands, has no odometry
(fc_bridge never sees it move), or misses a model or texture. Today those show
up only when someone opens that world by hand.
"""

import glob
import importlib.util
import os
from pathlib import Path
import re
from xml.etree import ElementTree

from ament_index_python.packages import get_package_prefix, get_package_share_directory
from launch import LaunchContext
from launch.actions import DeclareLaunchArgument
from launch.utilities import perform_substitutions
import pytest
import yaml

PACKAGE_DIR = Path(__file__).resolve().parents[1]
WORLDS_DIR = PACKAGE_DIR / 'worlds'
MODELS_DIR = PACKAGE_DIR / 'models'
BRIDGE = PACKAGE_DIR / 'config' / 'gz_bridge.yaml'
LAUNCH_FILE = PACKAGE_DIR / 'launch' / 'sim.launch.py'

# Gazebo names an <include> that has no <name> after the model inside it. For
# Fuel's "X3 UAV" that is x3: /model/x3/odometry, as gz_bridge.yaml reads it.
# A <name> on the include makes this table unnecessary.
FUEL_MODEL_NAMES = {'x3 uav': 'x3'}

# The drone's origin at start: on the ground, or just above it while it settles.
MAX_START_HEIGHT = 0.5


# ---------- reading SDF ----------

def norm(topic):
    """Write a Gazebo topic the way Gazebo resolves it: one leading slash, no doubles."""
    return '/' + '/'.join(part for part in topic.strip().split('/') if part)


def text(element, tag, default=None):
    child = element.find(tag)
    if child is None or child.text is None:
        return default
    return child.text.strip()


def kind(plugin):
    """Return the plugin's class: gz::sim::systems::Physics -> Physics."""
    return plugin.get('name', '').split('::')[-1]


def models_in(world):
    """Return every <model> and <include> in a world."""
    return list(world.iter('model')) + list(world.iter('include'))


def model_name(element):
    """Return the name Gazebo gives a <model> or <include>, or None if it can't be known here."""
    if element.tag == 'model':
        return element.get('name')
    name = text(element, 'name')
    if name:
        return name
    uri = text(element, 'uri', '')
    fuel = re.search(r'/models/([^/]+)', uri)
    if uri.startswith('http') and fuel:
        return FUEL_MODEL_NAMES.get(fuel.group(1).lower())
    if uri.startswith('model://'):
        sdf = model_sdf(MODELS_DIR / uri[len('model://'):].split('/')[0])
        if sdf is not None:
            return ElementTree.parse(sdf).getroot().find('model').get('name')
    return None


def model_sdf(model_dir):
    """Return the .sdf a model's model.config points to, or None."""
    config = model_dir / 'model.config'
    if not config.is_file():
        return None
    sdf = text(ElementTree.parse(config).getroot(), 'sdf')
    return model_dir / sdf if sdf else None


def velocity_topics(plugin):
    """Return (twist, enable) topics of a MulticopterVelocityControl plugin."""
    namespace = text(plugin, 'robotNamespace', '')
    return (norm(namespace + '/' + text(plugin, 'commandSubTopic', 'cmd_vel')),
            norm(namespace + '/' + text(plugin, 'enableSubTopic', 'enable')))


def bridge_topics():
    """Return the Gazebo side of gz_bridge.yaml: {twist, enable, odometry: set of topics}."""
    with open(BRIDGE) as f:
        entries = yaml.safe_load(f)

    def gz(direction, gz_type):
        return {norm(e['gz_topic_name']) for e in entries
                if e['direction'] == direction and e['gz_type_name'] == gz_type}
    return {'twist': gz('ROS_TO_GZ', 'gz.msgs.Twist'),
            'enable': gz('ROS_TO_GZ', 'gz.msgs.Boolean'),
            'odometry': gz('GZ_TO_ROS', 'gz.msgs.Odometry')}


# ---------- which worlds ----------

def default_world():
    spec = importlib.util.spec_from_file_location('sim_launch', LAUNCH_FILE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    for entity in module.generate_launch_description().entities:
        if isinstance(entity, DeclareLaunchArgument) and entity.name == 'world':
            return perform_substitutions(LaunchContext(), entity.default_value)
    raise AssertionError('sim.launch.py has no world argument')


def find_world(name):
    """Return the file gz sim opens for a world name: ours, GZ_SIM_RESOURCE_PATH, Gazebo's."""
    if os.path.isabs(name):
        return Path(name) if os.path.isfile(name) else None
    places = [WORLDS_DIR]
    places += [Path(d) for d in os.environ.get('GZ_SIM_RESOURCE_PATH', '').split(':') if d]
    try:
        gz = os.path.join(get_package_prefix('gz_sim_vendor'), 'opt', 'gz_sim_vendor')
        places += [Path(d) for d in sorted(glob.glob(f'{gz}/share/gz/gz-sim*/worlds'))]
    except LookupError:
        pass      # no Gazebo here (CI)
    return next((p / name for p in places if (p / name).is_file()), None)


def world_params():
    params = [pytest.param(p, id=p.name) for p in sorted(WORLDS_DIR.glob('*.sdf'))]
    name = default_world()
    if name not in [p.id for p in params]:
        path = find_world(name)
        if path is None:
            params.append(pytest.param(None, id=name, marks=pytest.mark.skip(
                reason=f"{name} is Gazebo's own world and Gazebo is not installed here "
                       '(CI); run_tests.sh in the dev container checks it')))
        else:
            params.append(pytest.param(path, id=name))
    return params


class World:
    def __init__(self, path):
        self.path = path
        root = ElementTree.parse(path).getroot()
        worlds = root.findall('world')
        assert root.tag == 'sdf' and len(worlds) == 1, f'{path}: not one <world> in <sdf>'
        self.element = worlds[0]


@pytest.fixture(params=world_params())
def world(request):
    return World(request.param)


@pytest.fixture(scope='module')
def bridge():
    return bridge_topics()


def the_drone(world, bridge):
    """Return the <model> or <include> whose velocity controller takes our commands."""
    found = []
    for element in models_in(world.element):
        for plugin in element.findall('plugin'):
            if kind(plugin) == 'MulticopterVelocityControl':
                twist, _ = velocity_topics(plugin)
                if twist in bridge['twist']:
                    found.append((element, plugin))
    assert len(found) == 1, (
        f'{world.path.name}: {len(found)} models take commands on {bridge["twist"]}; '
        'need exactly one, the drone')
    return found[0]


# ---------- the tests ----------

def test_bridge_talks_to_one_drone(bridge):
    for what, topics in bridge.items():
        assert len(topics) == 1, f'gz_bridge.yaml: {what} on {topics}, expected one topic'


def test_world_loads_physics(world):
    # A world with no plugins gets Gazebo's defaults, physics included.
    plugins = world.element.findall('plugin')
    assert not plugins or any(kind(p) == 'Physics' for p in plugins), (
        f'{world.path.name}: no gz-sim-physics-system plugin, so nothing would move')


def test_drone_takes_our_commands(world, bridge):
    _, plugin = the_drone(world, bridge)
    _, enable = velocity_topics(plugin)
    assert enable in bridge['enable'], (
        f'{world.path.name}: the drone is enabled on {enable}, the bridge sends to '
        f'{bridge["enable"]}; it would never start its motors')


def test_drone_publishes_the_odometry_we_read(world, bridge):
    element, _ = the_drone(world, bridge)
    odometry = [p for p in element.findall('plugin') if kind(p) == 'OdometryPublisher']
    assert odometry, (f'{world.path.name}: the drone has no OdometryPublisher, so no '
                      '/X3/odom: fc_bridge would never see it move')
    topic = text(odometry[0], 'odom_topic')
    if topic is None:
        name = model_name(element)
        assert name, (f"{world.path.name}: can't tell the drone's model name; "
                      'give its <include> a <name>')
        topic = f'/model/{name}/odometry'
    assert norm(topic) in bridge['odometry'], (
        f'{world.path.name}: the drone publishes odometry on {norm(topic)}, '
        f'the bridge reads {bridge["odometry"]}')


def test_drone_starts_on_the_ground(world, bridge):
    element, _ = the_drone(world, bridge)
    pose = (text(element, 'pose') or '0 0 0 0 0 0').split()
    assert 0.0 <= float(pose[2]) <= MAX_START_HEIGHT, (
        f'{world.path.name}: the drone starts at z = {pose[2]} m; the mission and '
        'test_sim_flight expect it on the ground')


def test_drone_fuel_model_is_pinned(world, bridge):
    # Without a version, a new upload to Fuel changes the drone under us.
    element, _ = the_drone(world, bridge)
    uri = text(element, 'uri', '')
    if uri.startswith('http'):
        assert re.search(r'/\d+/?$', uri), f'{world.path.name}: {uri} has no version'


def test_models_it_uses_exist(world):
    places = [MODELS_DIR] + [Path(d) for d in
                             os.environ.get('GZ_SIM_RESOURCE_PATH', '').split(':') if d]
    missing = []
    for element in world.element.iter('uri'):
        uri = (element.text or '').strip()
        if uri.startswith('model://'):
            name = uri[len('model://'):].split('/')[0]
            if not any((p / name / 'model.config').is_file() for p in places):
                missing.append(uri)
        elif uri and not uri.startswith(('http', 'file://', '/')) and '://' not in uri:
            if not (world.path.parent / uri).exists():
                missing.append(uri)
    assert not missing, f'{world.path.name}: not found: {missing}'


def model_dirs():
    return sorted(d for d in MODELS_DIR.iterdir() if d.is_dir()) if MODELS_DIR.is_dir() else []


def test_every_model_has_its_files():
    if not model_dirs():
        pytest.skip('no models in drone_bringup/models yet (they come with feature/153)')
    missing = []
    for model in model_dirs():
        sdf = model_sdf(model)
        if sdf is None or not sdf.is_file():
            missing.append(f'{model.name}: model.config or the .sdf it names')
            continue
        for element in ElementTree.parse(sdf).getroot().iter():
            if element.tag != 'uri' and not element.tag.endswith('_map'):
                continue
            ref = (element.text or '').strip()
            if ref.startswith('model://'):
                path = MODELS_DIR / ref[len('model://'):]
            elif ref and '://' not in ref and not ref.startswith('/'):
                path = sdf.parent / ref
            else:
                continue      # Fuel, absolute or empty: not ours to check
            if not path.exists():
                missing.append(f'{model.name}: {ref}')
    assert not missing, 'missing files:\n' + '\n'.join(missing)


def test_worlds_and_models_are_installed():
    ours = [Path('worlds') / p.name for p in sorted(WORLDS_DIR.glob('*.sdf'))]
    ours += [Path('models') / d.name / 'model.config' for d in model_dirs()]
    if not ours:
        pytest.skip('no worlds or models in drone_bringup yet (they come with feature/153)')
    share = Path(get_package_share_directory('drone_bringup'))
    missing = [str(p) for p in ours if not (share / p).is_file()]
    assert not missing, (f'not installed to {share}: {missing}; add the folder to '
                         'install(DIRECTORY ...) in CMakeLists.txt')
