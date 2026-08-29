"""Spiellogik: Bewegung, Kollisionsprüfung, Ausdauer, Türen und Gegenstände.

Reine Datenhaltung bleibt in `models.py`; hier kommt das Verhalten dazu, das
auf einem `GameState` operiert. Echte Gegnerbewegung und Sieg-/
Niederlage-Bedingungen folgen in späteren Meilensteinen.
"""

from __future__ import annotations

from wm_dungeon_crawler.models import MAX_STAMINA, Direction, GameState, Position


class Engine:
    """Wendet Spielregeln (Bewegung, Kollision, Ausdauer, Türen) auf einen
    GameState an."""

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
        Tastendruck. Liegt auf einem durchquerten Feld ein Gegenstand, wird
        er automatisch eingesammelt.

        Reihenfolge einer erfolgreichen Runde: Ausdauer wird abgezogen, die
        Spielfigur bewegt sich, Gegenstände auf dem Weg werden eingesammelt,
        alle Sicherheitskräfte ziehen (noch ohne Wirkung, siehe
        `_advance_guards`), danach regeneriert sich 1 Ausdauer.

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

        path: list[Position] = []
        position = self.state.player.position
        for _ in range(steps):
            position = position + direction
            if not self.is_passable(position):
                return False
            path.append(position)

        self.state.player.stamina -= cost
        self.state.player.position = position
        for step_position in path:
            self._collect_item_at(step_position)
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

    def try_unlock_adjacent_door(self) -> bool:
        """Schließt eine an die Spielfigur angrenzende verschlossene Tür auf.

        Verbraucht dabei genau einen Gegenstand aus dem Inventar (kein
        Generalschlüssel: jeder Gegenstand öffnet eine Tür und ist danach
        weg) und lässt anschließend die Sicherheitskräfte ziehen, kostet
        aber keine Ausdauer. Ist die Aktion nicht möglich (keine
        angrenzende verschlossene Tür, oder kein Gegenstand im Inventar),
        passiert nichts.

        >>> from wm_dungeon_crawler.models import Door, GameState, Grid, Item, Player, Position
        >>> grid = Grid(width=3, height=1)
        >>> door = Door(position=Position(1, 0))
        >>> player = Player(position=Position(0, 0))
        >>> engine = Engine(GameState(grid=grid, player=player, doors=[door]))
        >>> engine.try_unlock_adjacent_door()  # kein Gegenstand im Inventar
        False
        >>> player.inventory.append(Item(position=Position(0, 0), name="Trikot"))
        >>> engine.try_unlock_adjacent_door()
        True
        >>> door.locked
        False
        >>> player.inventory
        []
        """
        if not self.state.player.inventory:
            return False

        neighbor_positions = {
            self.state.player.position + direction for direction in Direction
        }
        for door in self.state.doors:
            if door.locked and door.position in neighbor_positions:
                door.locked = False
                self.state.player.inventory.pop()
                self._advance_guards()
                return True
        return False

    def _collect_item_at(self, position: Position) -> None:
        """Sammelt einen an dieser Position liegenden Gegenstand ins
        Inventar ein.

        >>> from wm_dungeon_crawler.models import GameState, Grid, Item, Player, Position
        >>> item = Item(position=Position(0, 0), name="Schlüssel")
        >>> player = Player(position=Position(0, 0))
        >>> engine = Engine(GameState(grid=Grid(width=1, height=1), player=player, items=[item]))
        >>> engine._collect_item_at(Position(0, 0))
        >>> engine.state.items
        []
        >>> player.inventory
        [Item(position=Position(x=0, y=0), name='Schlüssel')]
        """
        for item in list(self.state.items):
            if item.position == position:
                self.state.items.remove(item)
                self.state.player.inventory.append(item)

    def _advance_guards(self) -> None:
        """Lässt jede Sicherheitskraft ihren nächsten Patrouillenschritt tun.

        Noch ohne Wirkung – die eigentliche Bewegung folgt in Meilenstein 6
        (Gegnerbewegung und Niederlagebedingung).
        """
