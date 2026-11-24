"""
Tests for the plane sweep: rendered scenes with known distances, no ROS or Gazebo.

A scene is a list of upright rectangles facing the drone, each with a texture.
"""
import math

import cv2
from drone_sim import sweep as sw
import numpy as np
import pytest

CAM = sw.Camera()
W, H = 640, 480


def texture(seed, plain=None):
    """Return a 512x512 surface: random blobs, or one grey level."""
    if plain is not None:
        return np.full((512, 512), plain, np.float32)
    noise = np.random.default_rng(seed).random((512, 512)).astype(np.float32)
    blob = cv2.GaussianBlur(noise, (0, 0), 2)
    return cv2.normalize(blob, None, 20, 235, cv2.NORM_MINMAX)


def panel(x, half_width, tex, per_m, z=(-50, 50)):
    """Return an upright rectangle x m ahead of the origin."""
    return x, half_width, tex, per_m, z


BACK = panel(30.0, 200, texture(1), 12)
WALL = panel(4.0, 20, texture(2), 100)
PLAIN_PILLAR = panel(4.0, 0.25, texture(0, plain=90), 1)
BLANK = panel(4.0, 20, texture(0, plain=128), 1)


def pose(x, pitch=0.0, yaw=0.0, z=1.2):
    """Return the body pose; pitch > 0 is nose down, like ROS."""
    cp, sp, cy, sy = math.cos(pitch), math.sin(pitch), math.cos(yaw), math.sin(yaw)
    rot = (np.array([[cy, -sy, 0], [sy, cy, 0], [0, 0, 1.0]])
           @ np.array([[cp, 0, sp], [0, 1.0, 0], [-sp, 0, cp]]))
    return sw.Pose(np.array([x, 0.0, z]), rot)


def render(scene, p):
    """Return the grey image the camera sees from pose p."""
    sweep = sw.PlaneSweep()
    cam_rot = p.rot @ sweep.mount
    o = p.pos + p.rot @ sweep.offset
    f = (W / 2) / math.tan(CAM.hfov / 2)
    v, u = np.mgrid[0:H, 0:W]
    rays = np.stack([(u - (W - 1) / 2) / f, (v - (H - 1) / 2) / f,
                     np.ones(u.shape)], -1) @ cam_rot.T
    img = np.full((H, W), 128, np.float32)
    for x, half, tex, per_m, (z0, z1) in sorted(scene, key=lambda s: -s[0]):
        k = np.where(rays[..., 0] > 1e-3, (x - o[0]) / np.maximum(rays[..., 0], 1e-3), -1)
        y, z = o[1] + k * rays[..., 1], o[2] + k * rays[..., 2]
        hit = (k > 0) & (np.abs(y) < half) & (z > z0) & (z < z1)
        col = cv2.remap(tex, (y * per_m).astype(np.float32), (z * per_m).astype(np.float32),
                        cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)
        img[hit] = col[hit]
    return img.astype(np.uint8)


def fly(scene, poses, dt=0.1):
    """Fly through poses; return all results."""
    sweep = sw.PlaneSweep()
    return [sweep.update(render(scene, p), i * dt, p) for i, p in enumerate(poses)]


def forward(end, n=10, step=0.05, **kw):
    """Return poses flying forward, ending with the camera at x = end."""
    return [pose(end - CAM.forward - (n - 1 - i) * step, **kw) for i in range(n)]


@pytest.mark.parametrize('distance', [0.7, 1.0, 1.4])
def test_close_wall_is_an_obstacle(distance):
    r = fly([BACK, WALL], forward(4.0 - distance))[-1]
    assert r.state == sw.OBSTACLE
    assert r.distance == pytest.approx(distance, rel=0.1)


@pytest.mark.parametrize('distance', [0.7, 1.0, 1.3])
def test_plain_pillar_is_found_by_its_edges(distance):
    # With only its edges to go by it may read too close (the safe side), not too far.
    r = fly([BACK, PLAIN_PILLAR], forward(4.0 - distance))[-1]
    assert r.state == sw.OBSTACLE
    assert 0.7 * distance < r.distance < 1.15 * distance


def test_wall_further_than_the_warning_is_clear_with_a_distance():
    r = fly([BACK, WALL], forward(4.0 - 2.5))[-1]
    assert r.state == sw.CLEAR
    assert r.distance == pytest.approx(2.5, rel=0.15)


def test_far_scene_is_clear():
    r = fly([BACK], forward(2.0))[-1]
    assert r.state == sw.CLEAR


def test_blank_wall_is_unknown_never_clear():
    assert all(r.state == sw.UNKNOWN for r in fly([BLANK], forward(3.0)))


def test_nothing_visible_is_unknown_never_clear():
    assert all(r.state == sw.UNKNOWN for r in fly([], forward(3.0)))


def test_hovering_is_unknown():
    results = fly([BACK, WALL], [pose(2.0)] * 10)
    assert all(r.state == sw.UNKNOWN and r.reason == 'not moving' for r in results)


def test_unknown_distance_is_nan():
    assert math.isnan(fly([BACK, WALL], [pose(2.0)] * 3)[-1].distance)


def test_tilting_while_flying_forward():
    poses = [pose(3.0 - CAM.forward - (9 - i) * 0.05, pitch=0.02 * i) for i in range(10)]
    r = fly([BACK, WALL], poses)[-1]
    assert r.state == sw.OBSTACLE
    assert r.distance == pytest.approx(1.0, rel=0.15)


def test_turning_while_flying_forward():
    poses = [pose(3.0 - CAM.forward - (9 - i) * 0.05, yaw=0.02 * i) for i in range(10)]
    r = fly([BACK, WALL], poses)[-1]
    assert r.state == sw.OBSTACLE
    assert r.distance == pytest.approx(1.0, rel=0.2)


def test_low_over_the_floor_is_unknown():
    r = fly([BACK, WALL], forward(3.0, z=0.3))[-1]
    assert (r.state, r.reason) == (sw.UNKNOWN, 'too low')


def test_odometry_jump_starts_over():
    r = fly([BACK, WALL], forward(1.0) + [pose(2.9)])[-1]
    assert (r.state, r.reason) == (sw.UNKNOWN, 'odometry or time jumped')


def test_odometry_between_two_messages():
    buf = sw.OdomBuffer()
    buf.add(1.0, (0, 0, 1), (0, 0, 0, 1))
    buf.add(1.1, (1, 0, 1), (0, 0, math.sin(0.1), math.cos(0.1)))
    p = buf.at(1.05)
    assert p is not None
    assert p.pos == pytest.approx([0.5, 0, 1])
    assert math.atan2(p.rot[1, 0], p.rot[0, 0]) == pytest.approx(0.1, rel=1e-2)


def test_no_pose_outside_the_odometry_or_across_a_gap():
    buf = sw.OdomBuffer()
    buf.add(1.0, (0, 0, 1), (0, 0, 0, 1))
    buf.add(1.5, (1, 0, 1), (0, 0, 0, 1))
    assert buf.at(0.9) is None and buf.at(1.6) is None and buf.at(1.2) is None


def test_opposite_quaternions_are_the_same_attitude():
    buf = sw.OdomBuffer()
    buf.add(1.0, (0, 0, 1), (0, 0, 0, 1))
    buf.add(1.1, (0, 0, 1), (0, 0, 0, -1))
    p = buf.at(1.05)
    assert p is not None and p.rot == pytest.approx(np.eye(3))


def test_restarted_sim_forgets_old_odometry():
    buf = sw.OdomBuffer()
    buf.add(50.0, (0, 0, 1), (0, 0, 0, 1))
    buf.add(0.1, (0, 0, 1), (0, 0, 0, 1))
    assert buf.newest() == 0.1 and len(buf.rows) == 1


def test_corridor_box_is_around_the_flight_direction():
    sweep = sw.PlaneSweep()
    box = sweep.corridor_box(pose(0.0))
    assert box is not None
    (u0, v0), (u1, v1) = box
    f = sweep.k[0, 0]
    level = (sw.HEIGHT - 1) / 2 + f * math.tan(CAM.pitch_up)   # row that looks level
    assert u0 < (sw.WIDTH - 1) / 2 < u1
    assert v0 < level < v1


def test_climbing_is_not_flying_forward():
    # Height is noisy, so images from a climb are no base to measure with.
    results = fly([BACK, WALL], [pose(1.0, z=0.7 + 0.05 * i) for i in range(10)])
    assert all(r.state == sw.UNKNOWN and r.reason == 'not moving' for r in results)


def test_height_noise_is_smoothed():
    buf = sw.OdomBuffer()
    for i in range(20):
        buf.add(i * 0.02, (0, 0, 1.2 + (0.02 if i % 2 else -0.02)), (0, 0, 0, 1))
    p = buf.at(0.37)
    assert p is not None and p.pos[2] == pytest.approx(1.2, abs=0.006)


def test_blank_wall_with_a_visible_outline_is_an_obstacle():
    wall = panel(4.0, 2.0, texture(0, plain=200), 1, z=(0.0, 2.5))
    r = fly([BACK, wall], forward(4.0 - 1.4))[-1]
    assert r.state == sw.OBSTACLE
    assert r.distance == pytest.approx(1.4, rel=0.15)


def test_blank_sky_above_far_things_is_no_obstacle():
    low = panel(30.0, 200, texture(1), 12, z=(-50, 4))
    assert all(r.state != sw.OBSTACLE for r in fly([low], forward(3.0)))
