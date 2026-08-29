"""Startpunkt: ``uv run python -m wm_dungeon_crawler``.

Provisorische Text-Steuerung zum manuellen Testen von Bewegung, Kollision,
Ausdauer sowie Türen/Gegenständen – Platzhalter für die pygame-Oberfläche
aus Meilenstein 10.
"""

from wm_dungeon_crawler.engine import Engine
from wm_dungeon_crawler.levels import create_fixed_level
from wm_dungeon_crawler.models import MAX_STAMINA, Direction
from wm_dungeon_crawler.rendering import render_ascii

_WALK_KEYS: dict[str, Direction] = {
    "w": Direction.UP,
    "a": Direction.LEFT,
    "s": Direction.DOWN,
    "d": Direction.RIGHT,
}
_SPRINT_KEYS: dict[str, Direction] = {
    "W": Direction.UP,
    "A": Direction.LEFT,
    "S": Direction.DOWN,
    "D": Direction.RIGHT,
}


def _render_state(engine: Engine) -> None:
    print(render_ascii(engine.state))
    print(f"Ausdauer: {engine.state.player.stamina}/{MAX_STAMINA}")
    items = ", ".join(item.name for item in engine.state.player.inventory) or "leer"
    print(f"Inventar: {items}")


def main() -> None:
    """Lädt das feste Level und erlaubt provisorische Steuerung."""
    engine = Engine(create_fixed_level())
    _render_state(engine)
    print(
        "Steuerung: w/a/s/d gehen, W/A/S/D sprinten, "
        "r ausruhen, u Tür aufschließen, q beenden."
    )

    try:
        while True:
            command = input("> ").strip()
            if command == "q":
                print("Bis zum nächsten Mal!")
                break
            if command == "r":
                engine.take_turn_rest()
                _render_state(engine)
                continue
            if command == "u":
                if not engine.try_unlock_adjacent_door():
                    print(
                        "Das geht nicht - keine angrenzende Tür oder "
                        "kein Gegenstand im Inventar."
                    )
                _render_state(engine)
                continue
            direction = _WALK_KEYS.get(command)
            sprint = False
            if direction is None:
                direction = _SPRINT_KEYS.get(command)
                sprint = True
            if direction is None:
                print("Unbekannte Eingabe. Nutze w/a/s/d, W/A/S/D, r, u oder q.")
                continue
            if not engine.take_turn_move(direction, sprint=sprint):
                print("Das geht nicht - zu wenig Ausdauer oder der Weg ist versperrt.")
            _render_state(engine)
    except KeyboardInterrupt:
        print("\nAbbruch. Bis zum nächsten Mal!")


if __name__ == "__main__":
    main()
