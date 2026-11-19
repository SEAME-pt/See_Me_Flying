"""Shared setup for the telemetry tests: makes inav_telemetry importable.

telemetry/ is plain Python, not a ROS package, so colcon never runs these.
CI runs them in the telemetry-python job:  pytest telemetry -v
Locally, from the repo root:                python3 -m pytest telemetry -v
"""
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))


def reply(hex_frame):
    """Split a captured reply frame into (cmd, payload), checking it is whole."""
    frame = bytes.fromhex(hex_frame)
    assert frame[:3] == b"$X>", "not an MSP v2 reply"
    cmd = int.from_bytes(frame[4:6], "little")
    size = int.from_bytes(frame[6:8], "little")
    assert len(frame) == 8 + size + 1, "frame length does not match its size field"
    return cmd, frame[8:8 + size]
