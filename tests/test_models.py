"""Tests für die Datenmodell-Invarianten aus wm_dungeon_crawler.models."""

import pytest

from wm_dungeon_crawler.models import Grid, Guard, Player, Position, TileType


def test_grid_rejects_non_positive_dimensions():
    with pytest.raises(AssertionError):
        Grid(width=0, height=5)
    with pytest.raises(AssertionError):
        Grid(width=5, height=-1)


def test_grid_rejects_more_than_one_exit():
    tiles = {Position(0, 0): TileType.EXIT, Position(1, 0): TileType.EXIT}
    with pytest.raises(AssertionError):
        Grid(width=2, height=1, tiles=tiles)


def test_grid_untouched_tiles_default_to_floor():
    grid = Grid(width=2, height=2)
    assert grid.tile_at(Position(0, 0)) is TileType.FLOOR


def test_player_rejects_stamina_outside_valid_range():
    with pytest.raises(AssertionError):
        Player(position=Position(0, 0), stamina=-1)
    with pytest.raises(AssertionError):
        Player(position=Position(0, 0), stamina=3)


def test_guard_rejects_empty_patrol_route():
    with pytest.raises(AssertionError):
        Guard(patrol_route=[])


def test_guard_position_follows_patrol_index():
    guard = Guard(patrol_route=[Position(0, 0), Position(5, 5)], patrol_index=1)
    assert guard.position == Position(5, 5)
