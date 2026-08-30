"""Startpunkt: ``uv run python -m wm_dungeon_crawler``.

Provisorische Text-Steuerung zum manuellen Testen von Bewegung, Kollision,
Ausdauer, Türen/Gegenständen, Gegnern sowie Speichern/Laden – Platzhalter
für die pygame-Oberfläche aus Meilenstein 10.
"""

from wm_dungeon_crawler.engine import Engine
from wm_dungeon_crawler.levels import create_fixed_level
from wm_dungeon_crawler.models import MAX_STAMINA, Direction, GameStatus
from wm_dungeon_crawler.persistence import SaveFileError, load_game, save_game
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
    """Gibt Raster, Ausdauer und Inventar des aktuellen Zustands aus."""
    print(render_ascii(engine.state))
    print(f"Ausdauer: {engine.state.player.stamina}/{MAX_STAMINA}")
    items = ", ".join(item.name for item in engine.state.player.inventory) or "leer"
    print(f"Inventar: {items}")


def main() -> None:
    """Lädt das feste Level und erlaubt provisorische Steuerung."""
    engine = Engine(create_fixed_level())
    _render_state(engine)
    print(
        "Steuerung: w/a/s/d gehen, W/A/S/D sprinten, r ausruhen, "
        "u Tür aufschließen, save/load Spielstand, q beenden."
    )

    try:
        while engine.state.status is GameStatus.PLAYING:
            command = input("> ").strip()
            if command == "q":
                print("Bis zum nächsten Mal!")
                return
            if command == "save":
                save_game(engine.state)
                print("Spielstand gespeichert.")
            elif command == "load":
                try:
                    engine.state = load_game()
                    print("Spielstand geladen.")
                except SaveFileError as error:
                    print(f"Laden fehlgeschlagen: {error}")
            elif command == "r":
                engine.take_turn_rest()
            elif command == "u":
                if not engine.try_unlock_adjacent_door():
                    print(
                        "Das geht nicht - keine angrenzende Tür oder "
                        "kein Gegenstand im Inventar."
                    )
            else:
                direction = _WALK_KEYS.get(command)
                sprint = False
                if direction is None:
                    direction = _SPRINT_KEYS.get(command)
                    sprint = True
                if direction is None:
                    print(
                        "Unbekannte Eingabe. Nutze w/a/s/d, W/A/S/D, r, u, "
                        "save, load oder q."
                    )
                    continue
                if not engine.take_turn_move(direction, sprint=sprint):
                    print(
                        "Das geht nicht - zu wenig Ausdauer oder der Weg ist versperrt."
                    )
            _render_state(engine)

        if engine.state.status is GameStatus.LOST:
            print("Erwischt! Die Sicherheitskraft hat dich geschnappt. Game Over.")
        elif engine.state.status is GameStatus.WON:
            print("Geschafft! Du hast das Stadion verlassen. Gewonnen!")
    except KeyboardInterrupt:
        print("\nAbbruch. Bis zum nächsten Mal!")


if __name__ == "__main__":
    main()
