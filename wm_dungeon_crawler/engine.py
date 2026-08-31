"""Spiellogik: Bewegung, Kollision, Ausdauer, Türen/Gegenstände, Gegner sowie
Sieg- und Niederlagebedingung.

Reine Datenhaltung bleibt in `models.py`; hier kommt das Verhalten dazu, das
auf einem `GameState` operiert.
"""

from __future__ import annotations

from wm_dungeon_crawler.models import (
    MAX_STAMINA,
    Direction,
    GameState,
    GameStatus,
    Position,
)


class Engine:
    """Wendet Spielregeln (Bewegung, Kollision, Ausdauer, Türen, Gegner) auf
    einen GameState an."""

    def __init__(self, state: GameState) -> None:
        """Merkt sich den zu steuernden Spielzustand."""
        self.state = state

    def is_passable(self, position: Position) -> bool:
        """Prüft, ob eine Position betreten werden darf.

        Betretbar ist eine Position, wenn sie im Raster liegt, keine Wand
        ist und keine verschlossene Tür dort steht. Ob dort gerade eine
        Sicherheitskraft steht, spielt für die Bewegung keine Rolle – das
        führt stattdessen zur Niederlagebedingung.

        >>> from wm_dungeon_crawler.levels import create_fixed_level
        >>> engine = Engine(create_fixed_level())
        >>> engine.is_passable(Position(2, 1))
        True
        >>> engine.is_passable(Position(0, 0))
        False
        >>> engine.is_passable(Position(4, 7))
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
        verschlossene Tür, Rastergrenze, zu wenig Ausdauer oder die Partie
        ist bereits entschieden), passiert gar nichts und es wird keine
        Runde verbraucht.

        Reihenfolge einer erfolgreichen Runde: Ausdauer wird abgezogen, die
        Spielfigur bewegt sich, der Rundenzähler (`turns_taken`, Basis der
        Bestenliste in `highscores.py`) wird erhöht, Gegenstände auf dem Weg
        werden eingesammelt (was automatisch alle noch verschlossenen Türen
        aufschließt).
        Steht die Spielfigur danach auf dem Ausgang, ist die Partie sofort
        gewonnen. Andernfalls: landet sie auf einer Sicherheitskraft, ist
        die Partie sofort verloren; sonst ziehen alle Sicherheitskräfte, was
        ebenfalls zur Niederlage führen kann; nur wenn die Partie danach
        noch läuft, regeneriert sich 1 Ausdauer.

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
        Position(x=2, y=6)
        """
        if self.state.status is not GameStatus.PLAYING:
            return False

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
        self.state.turns_taken += 1
        for step_position in path:
            self._collect_item_at(step_position)
        self._check_won()
        if self.state.status is GameStatus.PLAYING:
            self._check_caught()
        if self.state.status is GameStatus.PLAYING:
            self._advance_guards()
            self._check_caught()
        if self.state.status is GameStatus.PLAYING:
            self.state.player.stamina = min(self.state.player.stamina + 1, MAX_STAMINA)
        return True

    def take_turn_rest(self) -> None:
        """Lässt die Spielfigur eine Runde ausruhen.

        Keine Bewegung, keine Ausdauerkosten, aber der Rundenzähler
        (`turns_taken`) wird trotzdem erhöht. Danach ziehen alle
        Sicherheitskräfte, was zur Niederlage führen kann; nur wenn die
        Partie danach noch läuft, wird die Ausdauerleiste vollständig
        aufgefüllt. Ist die Partie bereits entschieden, passiert nichts.

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
        if self.state.status is not GameStatus.PLAYING:
            return
        self.state.turns_taken += 1
        self._advance_guards()
        self._check_caught()
        if self.state.status is GameStatus.PLAYING:
            self.state.player.stamina = MAX_STAMINA

    def _collect_item_at(self, position: Position) -> None:
        """Sammelt einen an dieser Position liegenden Gegenstand ins
        Inventar ein und schließt dabei automatisch alle noch
        verschlossenen Türen auf.

        Der Gegenstand bleibt im Inventar (u.a. damit die GUI weiterhin
        erkennen kann, dass die Spielfigur ihn trägt und den passenden
        Sprite zeigt) – anders als bei einem klassischen Schlüssel gibt es
        kein manuelles Aufschließen und kein Verbrauchen mehr.

        >>> from wm_dungeon_crawler.models import Door, GameState, Grid, Item, Player, Position
        >>> item = Item(position=Position(0, 0), name="Trikot")
        >>> door = Door(position=Position(1, 0))
        >>> player = Player(position=Position(0, 0))
        >>> state = GameState(
        ...     grid=Grid(width=2, height=1), player=player, items=[item], doors=[door]
        ... )
        >>> engine = Engine(state)
        >>> engine._collect_item_at(Position(0, 0))
        >>> engine.state.items
        []
        >>> player.inventory
        [Item(position=Position(x=0, y=0), name='Trikot')]
        >>> door.locked
        False
        """
        for item in list(self.state.items):
            if item.position == position:
                self.state.items.remove(item)
                self.state.player.inventory.append(item)
                for door in self.state.doors:
                    door.locked = False

    def _advance_guards(self) -> None:
        """Lässt jede Sicherheitskraft ihren nächsten Patrouillenschritt tun.

        >>> from wm_dungeon_crawler.models import GameState, Grid, Guard, Player, Position
        >>> guard = Guard(patrol_route=[Position(0, 0), Position(1, 0), Position(2, 0)])
        >>> engine = Engine(GameState(
        ...     grid=Grid(width=3, height=1),
        ...     player=Player(position=Position(0, 0)),
        ...     guards=[guard],
        ... ))
        >>> engine._advance_guards()
        >>> guard.position
        Position(x=1, y=0)
        >>> engine._advance_guards()
        >>> guard.position
        Position(x=2, y=0)
        >>> engine._advance_guards()  # Patrouillenweg beginnt zyklisch von vorn
        >>> guard.position
        Position(x=0, y=0)
        """
        for guard in self.state.guards:
            guard.patrol_index = (guard.patrol_index + 1) % len(guard.patrol_route)

    def _check_won(self) -> None:
        """Setzt den Spielstatus auf WON, wenn die Spielfigur einen der
        Ausgänge erreicht hat (ein Level kann mehrere gleichwertige
        Ausgänge haben, siehe `Grid.exit_positions`).

        >>> from wm_dungeon_crawler.models import GameState, GameStatus, Grid, Player, Position, TileType
        >>> grid = Grid(width=2, height=1, tiles={Position(1, 0): TileType.EXIT})
        >>> engine = Engine(GameState(grid=grid, player=Player(position=Position(1, 0))))
        >>> engine.state.status is GameStatus.PLAYING
        True
        >>> engine._check_won()
        >>> engine.state.status is GameStatus.WON
        True
        """
        if self.state.player.position in self.state.grid.exit_positions:
            self.state.status = GameStatus.WON

    def _check_caught(self) -> None:
        """Setzt den Spielstatus auf LOST, wenn eine Sicherheitskraft und
        die Spielfigur auf demselben Feld stehen.

        >>> from wm_dungeon_crawler.models import GameState, GameStatus, Grid, Guard, Player, Position
        >>> engine = Engine(GameState(
        ...     grid=Grid(width=2, height=1),
        ...     player=Player(position=Position(0, 0)),
        ...     guards=[Guard(patrol_route=[Position(0, 0)])],
        ... ))
        >>> engine.state.status is GameStatus.PLAYING
        True
        >>> engine._check_caught()
        >>> engine.state.status is GameStatus.LOST
        True
        """
        if any(
            guard.position == self.state.player.position for guard in self.state.guards
        ):
            self.state.status = GameStatus.LOST
