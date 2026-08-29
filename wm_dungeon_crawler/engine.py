"""Spiellogik: Bewegung, Kollisionsprüfung und Ausdauer.

Reine Datenhaltung bleibt in `models.py`; hier kommt das Verhalten dazu, das
auf einem `GameState` operiert. Türen aufschließen, echte Gegnerbewegung und
Sieg-/Niederlage-Bedingungen folgen in späteren Meilensteinen.
"""

from __future__ import annotations

from wm_dungeon_crawler.models import MAX_STAMINA, Direction, GameState, Position


class Engine:
    """Wendet Spielregeln (Bewegung, Kollision, Ausdauer) auf einen GameState an."""

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

    def take_turn_move(self, direction: Direction, *, sprint: bool = False) -> bool:
        """Bewegt die Spielfigur und schließt damit eine Spielrunde ab.

        Ohne Sprint: ein Schritt für 1 Ausdauer. Mit Sprint: zwei Schritte in
        dieselbe Richtung für 2 Ausdauer (nur bei voller Ausdauerleiste
        möglich, die maximal 2 fasst). Ist die Bewegung nicht möglich (Wand,
        verschlossene Tür, Rastergrenze oder zu wenig Ausdauer), passiert gar
        nichts und es wird keine Runde verbraucht – wie ein ungültiger
        Tastendruck.

        Reihenfolge einer erfolgreichen Runde: Ausdauer wird abgezogen, die
        Spielfigur bewegt sich, alle Sicherheitskräfte ziehen (noch ohne
        Wirkung, siehe `_advance_guards`), danach regeneriert sich 1 Ausdauer.

        >>> from wm_dungeon_crawler.levels import create_fixed_level
        >>> engine = Engine(create_fixed_level())
        >>> engine.take_turn_move(Direction.DOWN)
        True
        >>> engine.state.player.stamina  # 2 - 1 (Schritt) + 1 (Regeneration)
        2
        >>> engine.take_turn_move(Direction.DOWN, sprint=True)
        True
        >>> engine.state.player.stamina  # 2 - 2 (Sprint) + 1 (Regeneration)
        1
        >>> engine.take_turn_move(Direction.UP, sprint=True)  # nur 1 Ausdauer übrig
        False
        >>> engine.state.player.position  # unverändert, Fehlversuch kostet nichts
        Position(x=2, y=4)
        """
        steps = 2 if sprint else 1
        cost = steps
        if self.state.player.stamina < cost:
            return False

        position = self.state.player.position
        for _ in range(steps):
            position = position + direction
            if not self.is_passable(position):
                return False

        self.state.player.stamina -= cost
        self.state.player.position = position
        self._advance_guards()
        self.state.player.stamina = min(self.state.player.stamina + 1, MAX_STAMINA)
        return True

    def take_turn_rest(self) -> None:
        """Lässt die Spielfigur eine Runde ausruhen.

        Keine Bewegung, keine Ausdauerkosten; nach dem Zug der
        Sicherheitskräfte wird die Ausdauerleiste vollständig aufgefüllt.

        >>> from wm_dungeon_crawler.levels import create_fixed_level
        >>> engine = Engine(create_fixed_level())
        >>> engine.take_turn_move(Direction.DOWN, sprint=True)
        True
        >>> engine.state.player.stamina
        1
        >>> engine.take_turn_rest()
        >>> engine.state.player.stamina
        2
        """
        self._advance_guards()
        self.state.player.stamina = MAX_STAMINA

    def _advance_guards(self) -> None:
        """Lässt jede Sicherheitskraft ihren nächsten Patrouillenschritt tun.

        Noch ohne Wirkung – die eigentliche Bewegung folgt in Meilenstein 6
        (Gegnerbewegung und Niederlagebedingung).
        """
