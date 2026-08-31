"""Tests für die Datenmodell-Invarianten aus wm_dungeon_crawler.models."""

import pytest

from wm_dungeon_crawler.models import Grid, Guard, Player, Position, TileType


def test_grid_rejects_non_positive_dimensions() -> None:
    with pytest.raises(AssertionError):
        Grid(width=0, height=5)
    with pytest.raises(AssertionError):
        Grid(width=5, height=-1)


def test_grid_supports_multiple_exits() -> None:
    tiles = {Position(0, 0): TileType.EXIT, Position(1, 0): TileType.EXIT}
    grid = Grid(width=2, height=1, tiles=tiles)
    assert grid.exit_positions == {Position(0, 0), Position(1, 0)}


def test_grid_untouched_tiles_default_to_floor() -> None:
    grid = Grid(width=2, height=2)
    assert grid.tile_at(Position(0, 0)) is TileType.FLOOR


def test_grid_pitch_is_not_walkable() -> None:
    grid = Grid(width=2, height=1, tiles={Position(1, 0): TileType.PITCH})
    assert grid.is_walkable(Position(1, 0)) is False


def test_player_rejects_stamina_outside_valid_range() -> None:
    with pytest.raises(AssertionError):
        Player(position=Position(0, 0), stamina=-1)
    with pytest.raises(AssertionError):
        Player(position=Position(0, 0), stamina=3)


def test_guard_rejects_empty_patrol_route() -> None:
    with pytest.raises(AssertionError):
        Guard(patrol_route=[])


def test_guard_position_follows_patrol_index() -> None:
    guard = Guard(patrol_route=[Position(0, 0), Position(5, 5)], patrol_index=1)
    assert guard.position == Position(5, 5)
