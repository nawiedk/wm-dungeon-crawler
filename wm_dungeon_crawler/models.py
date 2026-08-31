"""Datenmodell für Spielfeld, Spielfigur, Gegner und Gegenstände.

Enthält ausschließlich Datenstrukturen (keine Zug-/Bewegungslogik – die folgt
in einem späteren Schritt). Koordinatenkonvention: x wächst nach rechts,
y wächst nach unten (Zeile 0 ist oben), passend zur späteren Darstellung mit
pygame.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Final

MAX_STAMINA: Final[int] = 2


class Direction(Enum):
    """Die vier erlaubten Bewegungsrichtungen (kein Diagonal-Movement)."""

    UP = (0, -1)
    DOWN = (0, 1)
    LEFT = (-1, 0)
    RIGHT = (1, 0)


@dataclass(frozen=True, order=True)
class Position:
    """Eine Rasterposition im Stadion.

    Sortierbar (erst x, dann y) – nützlich, um Mengen von Positionen für
    Ausgaben/Tests in eine reproduzierbare Reihenfolge zu bringen.

    >>> Position(2, 3) == Position(2, 3)
    True
    >>> Position(0, 0) + Direction.RIGHT
    Position(x=1, y=0)
    >>> sorted([Position(1, 0), Position(0, 1), Position(0, 0)])
    [Position(x=0, y=0), Position(x=0, y=1), Position(x=1, y=0)]
    """

    x: int
    y: int

    def __add__(self, direction: Direction) -> Position:
        """Addiert eine Bewegungsrichtung auf diese Position."""
        dx, dy = direction.value
        return Position(self.x + dx, self.y + dy)


class TileType(Enum):
    """Die Beschaffenheit eines Rasterfelds."""

    FLOOR = "floor"
    WALL = "wall"
    EXIT = "exit"
    PITCH = "pitch"  # der Fußballplatz in der Mitte des Stadions: nicht begehbar
    BARRIER = "barrier"  # dauerhaftes Hindernis, optisch von WALL unterschieden


@dataclass
class Grid:
    """Das Rasterfeld des Stadions: Abmessungen und Beschaffenheit jeder Zelle.

    Nicht explizit gesetzte Felder gelten als begehbarer Boden (FLOOR).

    >>> grid = Grid(width=3, height=2, tiles={Position(0, 0): TileType.WALL})
    >>> grid.in_bounds(Position(0, 0))
    True
    >>> grid.in_bounds(Position(3, 0))
    False
    >>> grid.tile_at(Position(0, 0)) is TileType.WALL
    True
    >>> grid.tile_at(Position(1, 0)) is TileType.FLOOR
    True
    >>> grid.is_walkable(Position(0, 0))
    False
    >>> grid.is_walkable(Position(1, 0))
    True
    """

    width: int
    height: int
    tiles: dict[Position, TileType] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Prüft, dass die Rastermaße positiv sind."""
        assert self.width > 0 and self.height > 0, "Rastermaße müssen positiv sein"

    def in_bounds(self, position: Position) -> bool:
        """Prüft, ob eine Position innerhalb der Rastergrenzen liegt."""
        return 0 <= position.x < self.width and 0 <= position.y < self.height

    def tile_at(self, position: Position) -> TileType:
        """Liefert den Feldtyp einer Position (FLOOR, falls nicht gesetzt)."""
        return self.tiles.get(position, TileType.FLOOR)

    def is_walkable(self, position: Position) -> bool:
        """Prüft, ob eine Position im Raster liegt und begehbar ist.

        Begehbar sind FLOOR und EXIT; WALL und PITCH (der Fußballplatz)
        nicht. Bewusst als Positivliste formuliert, damit ein künftiger,
        weiterer nicht-begehbarer Feldtyp nicht vergessen werden kann.
        """
        if not self.in_bounds(position):
            return False
        return self.tile_at(position) in (TileType.FLOOR, TileType.EXIT)

    @property
    def exit_positions(self) -> set[Position]:
        """Alle Positionen, die als Ausgang gelten.

        Ein Level kann mehrere gleichwertige Ausgänge haben (z.B. einen
        frei zugänglichen, aber riskanteren, und einen versperrten,
        sichereren) – jeder von ihnen gewinnt die Partie.

        >>> grid = Grid(width=3, height=1, tiles={
        ...     Position(0, 0): TileType.EXIT, Position(2, 0): TileType.EXIT,
        ... })
        >>> sorted(grid.exit_positions)
        [Position(x=0, y=0), Position(x=2, y=0)]
        """
        return {
            position for position, tile in self.tiles.items() if tile is TileType.EXIT
        }


@dataclass
class Door:
    """Eine Tür an einer festen Rasterposition, die verschlossen sein kann."""

    position: Position
    locked: bool = True


@dataclass
class Item:
    """Ein aufsammelbarer Gegenstand (z.B. Schlüssel oder Trikot).

    Alle Gegenstände wirken identisch als genereller Türöffner-Mechanismus und
    unterscheiden sich nur in ihrer Bezeichnung.

    >>> Item(position=Position(1, 1), name="Trikot").name
    'Trikot'
    """

    position: Position
    name: str


@dataclass
class Player:
    """Die von der Nutzerin gesteuerte Spielfigur.

    >>> player = Player(position=Position(0, 0))
    >>> player.stamina
    2
    >>> Player(position=Position(0, 0), stamina=99)
    Traceback (most recent call last):
    ...
    AssertionError: Ausdauer muss zwischen 0 und 2 liegen
    """

    position: Position
    stamina: int = MAX_STAMINA
    inventory: list[Item] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Prüft, dass die Ausdauer im gültigen Bereich liegt."""
        assert 0 <= self.stamina <= MAX_STAMINA, (
            f"Ausdauer muss zwischen 0 und {MAX_STAMINA} liegen"
        )


@dataclass
class Guard:
    """Eine Sicherheitskraft, die einen festen Patrouillenweg zyklisch abläuft.

    Die aktuelle Position ergibt sich aus dem Patrouillenweg und einem Index,
    statt redundant gespeichert zu werden.

    >>> guard = Guard(patrol_route=[Position(0, 0), Position(1, 0)])
    >>> guard.position
    Position(x=0, y=0)
    """

    patrol_route: list[Position]
    patrol_index: int = 0

    def __post_init__(self) -> None:
        """Prüft, dass der Patrouillenweg nicht leer und der Index gültig ist."""
        assert len(self.patrol_route) > 0, "Patrouillenweg darf nicht leer sein"
        assert 0 <= self.patrol_index < len(self.patrol_route), (
            "patrol_index außerhalb des Patrouillenwegs"
        )

    @property
    def position(self) -> Position:
        """Die aktuelle Position entlang des Patrouillenwegs."""
        return self.patrol_route[self.patrol_index]


class GameStatus(Enum):
    """Der Ausgang einer Partie."""

    PLAYING = "playing"
    WON = "won"
    LOST = "lost"


@dataclass
class GameState:
    """Der vollständige Zustand einer laufenden Partie."""

    grid: Grid
    player: Player
    guards: list[Guard] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)
    doors: list[Door] = field(default_factory=list)
    status: GameStatus = GameStatus.PLAYING
