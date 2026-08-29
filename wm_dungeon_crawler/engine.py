"""Spiellogik: Bewegung und Kollisionsprüfung.

Reine Datenhaltung bleibt in `models.py`; hier kommt das Verhalten dazu, das
auf einem `GameState` operiert. Ausdauerkosten, Türen aufschließen,
Gegnerbewegung und Sieg-/Niederlage-Bedingungen folgen in späteren
Meilensteinen und sind hier bewusst noch nicht enthalten.
"""

from __future__ import annotations

from wm_dungeon_crawler.models import Direction, GameState, Position


class Engine:
    """Wendet Spielregeln auf einen GameState an.

    >>> from wm_dungeon_crawler.levels import create_fixed_level
    >>> engine = Engine(create_fixed_level())
    >>> engine.state.player.position
    Position(x=2, y=1)
    >>> engine.try_move_player(Direction.RIGHT)  # dort ist eine Wand
    False
    >>> engine.try_move_player(Direction.DOWN)
    True
    >>> engine.state.player.position
    Position(x=2, y=2)
    """

    def __init__(self, state: GameState) -> None:
        self.state = state

    def is_passable(self, position: Position) -> bool:
        """Prüft, ob eine Position betreten werden darf.

        Betretbar ist eine Position, wenn sie im Raster liegt, keine Wand
        ist und keine verschlossene Tür dort steht. Ob dort gerade eine
        Sicherheitskraft steht, spielt für die Bewegung keine Rolle – das
        führt stattdessen zur Niederlagebedingung (späterer Meilenstein).

        >>> from wm_dungeon_crawler.levels import create_fixed_level
        >>> engine = Engine(create_fixed_level())
        >>> engine.is_passable(Position(2, 2))
        True
        >>> engine.is_passable(Position(0, 0))
        False
        >>> engine.is_passable(Position(2, 9))
        False
        """
        if not self.state.grid.is_walkable(position):
            return False
        return not any(
            door.position == position and door.locked for door in self.state.doors
        )

    def try_move_player(self, direction: Direction) -> bool:
        """Versucht, die Spielfigur einen Schritt weit zu bewegen.

        Gibt zurück, ob die Bewegung ausgeführt wurde. Ausdauerkosten und
        Sprint-Verhalten kommen erst mit dem nächsten Meilenstein dazu.
        """
        target = self.state.player.position + direction
        if not self.is_passable(target):
            return False
        self.state.player.position = target
        return True
