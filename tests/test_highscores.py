"""Tests für die Bestenliste in wm_dungeon_crawler.highscores."""

import tempfile
from pathlib import Path

from hypothesis import given
from hypothesis import strategies as st

from wm_dungeon_crawler.highscores import MAX_ENTRIES, load_highscores, record_attempt


def test_load_missing_file_returns_empty_list(tmp_path: Path) -> None:
    assert load_highscores(tmp_path / "nope.json") == []


def test_load_corrupted_file_returns_empty_list(tmp_path: Path) -> None:
    bad_path = tmp_path / "broken.json"
    bad_path.write_text("{not valid json", encoding="utf-8")
    assert load_highscores(bad_path) == []


def test_record_first_attempt(tmp_path: Path) -> None:
    path = tmp_path / "highscores.json"
    assert record_attempt(12, path) == [12]
    assert load_highscores(path) == [12]


def test_record_keeps_only_the_fewest_turns(tmp_path: Path) -> None:
    path = tmp_path / "highscores.json"
    record_attempt(10, path)
    record_attempt(5, path)
    record_attempt(8, path)

    result = record_attempt(20, path)

    assert result == [5, 8, 10]


@given(st.lists(st.integers(min_value=0, max_value=1000), min_size=1, max_size=15))
def test_highscores_always_hold_the_fewest_seen_sorted_ascending(
    attempts: list[int],
) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "highscores.json"
        result: list[int] = []
        for turns in attempts:
            result = record_attempt(turns, path)

        assert result == sorted(attempts)[:MAX_ENTRIES]
        assert result == sorted(result)
