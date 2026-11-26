"""Tests for the floor map: plain Python, no ROS needed."""

from drone_sim.floor_map import FloorMap
import pytest

DATA = {
    'default': 'carpet',
    'surfaces': {'carpet': {'quality': 100}, 'mat': {'quality': 60},
                 'table': {'quality': 0}},
    'areas': [
        {'surface': 'table', 'x': [0.0, 2.0], 'y': [0.0, 1.0]},
        {'surface': 'mat', 'x': [1.5, 2.5], 'y': [0.5, 1.5]},
    ],
}


def test_default_surface_outside_every_area():
    assert FloorMap(DATA).quality(-3.0, -3.0) == 100


def test_inside_an_area():
    assert FloorMap(DATA).quality(0.5, 0.5) == 0


def test_later_area_wins_where_they_overlap():
    assert FloorMap(DATA).quality(1.8, 0.8) == 60


def test_edges_count_as_inside():
    assert FloorMap(DATA).quality(0.0, 0.0) == 0


def test_unknown_surface_is_an_error():
    bad = dict(DATA, areas=[{'surface': 'tile', 'x': [0.0, 1.0], 'y': [0.0, 1.0]}])
    with pytest.raises(ValueError):
        FloorMap(bad)


def test_the_room_map_loads():
    path = __file__.rsplit('/drone_sim/', 1)[0] + '/drone_bringup/worlds/room_world_surfaces.yaml'
    FloorMap.load(path)
