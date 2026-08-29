"""Startpunkt: ``uv run python -m wm_dungeon_crawler``.

Provisorische Text-Steuerung zum manuellen Testen von Bewegung und
Kollision – Platzhalter für die pygame-Oberfläche aus Meilenstein 10.
"""

from wm_dungeon_crawler.engine import Engine
from wm_dungeon_crawler.levels import create_fixed_level
from wm_dungeon_crawler.models import Direction
from wm_dungeon_crawler.rendering import render_ascii

_KEYS: dict[str, Direction] = {
    "w": Direction.UP,
    "a": Direction.LEFT,
    "s": Direction.DOWN,
    "d": Direction.RIGHT,
}


def main() -> None:
    """Lädt das feste Level und erlaubt provisorische Steuerung über w/a/s/d."""
    engine = Engine(create_fixed_level())
    print(render_ascii(engine.state))
    print("Steuerung: w/a/s/d bewegen, q beenden.")

    try:
        while True:
            command = input("> ").strip().lower()
            if command == "q":
                print("Bis zum nächsten Mal!")
                break
            direction = _KEYS.get(command)
            if direction is None:
                print("Unbekannte Eingabe. Nutze w/a/s/d oder q.")
                continue
            if not engine.try_move_player(direction):
                print("Das geht nicht - dort ist eine Wand oder eine verschlossene Tür.")
            print(render_ascii(engine.state))
    except KeyboardInterrupt:
        print("\nAbbruch. Bis zum nächsten Mal!")


if __name__ == "__main__":
    main()
