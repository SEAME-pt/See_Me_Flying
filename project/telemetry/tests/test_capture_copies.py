"""The copies of the drone recordings in project/ros2 must match the originals here.

fc_bridge's C++ tests (drone_fc_bridge/test/data/, ROS-6 step A) read copies of
the recordings in project/telemetry/inav/msp/captures/, because a ROS package must
hold its own test data (colcon builds and tests each package on its own). If the
captures are redone, copy them there again. Both test suites check exact values
from these files, so if one copy is redone and the other is not, the C++ and
Python tests quietly test different data. This makes that rule a check.

Runs in CI's telemetry-python job, which checks out the whole repo. Copies are
found by name anywhere under project/ros2/src, so moving them is fine.
"""
from pathlib import Path

import pytest

TELEMETRY = Path(__file__).resolve().parents[1]
CAPTURES = TELEMETRY / "inav" / "msp" / "captures"
REPO = TELEMETRY.parent   # project/
ROS_SRC = REPO / "ros2" / "src"


def originals():
    """{file name: path} of the recordings."""
    return {p.name: p for p in sorted(CAPTURES.glob("*.jsonl"))}


def copies(names):
    """Every file under project/ros2/src with the name of a recording."""
    return sorted(p for p in ROS_SRC.rglob("*.jsonl") if p.name in names)


def test_recordings_are_where_this_test_looks():
    # Without this, moving the recordings would make the test below skip quietly.
    assert sorted(originals()) == [
        "flat_still.jsonl", "flow_moving.jsonl", "radio_off.jsonl", "tilted.jsonl"]


def test_copies_in_ros2_match_the_recordings():
    if not ROS_SRC.is_dir():
        pytest.skip(f"telemetry/ is not inside the repo here ({TELEMETRY}), so there is "
                    "no project/ros2 to compare with")
    found = originals()
    copied = copies(found)
    if not copied:
        pytest.skip("no copies under project/ros2/src yet "
                    "(they come with fc_bridge's C++ tests, ROS-6 step A)")
    different = [c for c in copied if c.read_bytes() != found[c.name].read_bytes()]
    assert not different, "copies that differ from the recording:\n" + "\n".join(
        f"  {c.relative_to(REPO)}  (to copy again: cp "
        f"{found[c.name].relative_to(REPO)} {c.relative_to(REPO)})" for c in different)
