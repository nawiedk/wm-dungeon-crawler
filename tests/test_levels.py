"""Tests für das Laden von Leveln aus wm_dungeon_crawler.levels."""

import pytest

from wm_dungeon_crawler.levels import create_fixed_level, parse_level


def test_parse_level_rejects_ragged_lines():
    with pytest.raises(ValueError, match="gleich lang"):
        parse_level("###\n#P\n###")


def test_parse_level_rejects_unknown_character():
    with pytest.raises(ValueError, match="Unbekanntes Zeichen"):
        parse_level("###\n#X#\n###")


def test_parse_level_requires_player_start():
    with pytest.raises(ValueError, match="Startposition"):
        parse_level("###\n#.#\n###")


def test_parse_level_rejects_empty_description():
    with pytest.raises(ValueError, match="leer"):
        parse_level("   \n\n")


def test_create_fixed_level_is_internally_consistent():
    state = create_fixed_level()

    assert state.grid.exit_positions
    assert state.grid.is_walkable(state.player.position)
    for guard in state.guards:
        for waypoint in guard.patrol_route:
            assert state.grid.is_walkable(waypoint)
    for item in state.items:
        assert state.grid.is_walkable(item.position)
    for door in state.doors:
        assert state.grid.in_bounds(door.position)
