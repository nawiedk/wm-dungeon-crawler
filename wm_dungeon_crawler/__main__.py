"""Startpunkt: ``uv run python -m wm_dungeon_crawler`` zeigt das feste Level."""

from wm_dungeon_crawler.levels import create_fixed_level
from wm_dungeon_crawler.rendering import render_ascii


def main() -> None:
    """Lädt das feste Level und gibt es als Text aus."""
    state = create_fixed_level()
    print(render_ascii(state))


if __name__ == "__main__":
    main()
