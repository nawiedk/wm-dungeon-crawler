"""Tests für Speichern/Laden aus wm_dungeon_crawler.persistence."""

import tempfile
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from wm_dungeon_crawler.levels import create_fixed_level
from wm_dungeon_crawler.persistence import SaveFileError, load_game, save_game


def test_round_trip_preserves_player_and_level_shape(tmp_path):
    state = create_fixed_level()
    state.player.stamina = 1
    save_path = tmp_path / "save.json"

    save_game(state, save_path)
    loaded = load_game(save_path)

    assert loaded.player.position == state.player.position
    assert loaded.player.stamina == 1
    assert (loaded.grid.width, loaded.grid.height) == (
        state.grid.width,
        state.grid.height,
    )
    assert len(loaded.guards) == len(state.guards)
    assert len(loaded.doors) == len(state.doors)
    assert len(loaded.items) == len(state.items)


def test_load_missing_file_raises_save_file_error(tmp_path):
    with pytest.raises(SaveFileError, match="Keine Speicherdatei"):
        load_game(tmp_path / "nope.json")


def test_load_corrupted_json_raises_save_file_error(tmp_path):
    bad_path = tmp_path / "broken.json"
    bad_path.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(SaveFileError, match="ungültig"):
        load_game(bad_path)


def test_load_valid_json_with_wrong_shape_raises_save_file_error(tmp_path):
    bad_path = tmp_path / "wrong_shape.json"
    bad_path.write_text('{"just": "not a save file"}', encoding="utf-8")
    with pytest.raises(SaveFileError):
        load_game(bad_path)


@given(st.integers(min_value=0, max_value=2))
def test_round_trip_preserves_arbitrary_valid_stamina(stamina):
    state = create_fixed_level()
    state.player.stamina = stamina
    with tempfile.TemporaryDirectory() as tmp:
        save_path = Path(tmp) / "save.json"
        save_game(state, save_path)
        loaded = load_game(save_path)
    assert loaded.player.stamina == stamina
