"""Laden eines Levels aus einer ASCII-Beschreibung.

Level werden als mehrzeilige Zeichenkunst definiert und geparst. Das hält die
konkrete Level-Geometrie unabhängig davon, wie sie später dargestellt wird
(Text vorerst, pygame ab einem späteren Meilenstein) – Trennung von
Spiellogik und Darstellung.

Zeichen:
    '#'  Wand
    '.'  begehbarer Boden
    'E'  Ausgang
    'D'  verschlossene Tür (auf begehbarem Boden)
    'i'  Gegenstand (Schlüssel/Trikot, auf begehbarem Boden)
    'P'  Startposition der Spielfigur (auf begehbarem Boden)

Patrouillenwege von Sicherheitskräften lassen sich in einer einzelnen
Zeichenkunst nicht sinnvoll als geordnete Wegpunkte ausdrücken und werden
daher separat in Code angegeben, siehe `create_fixed_level`.
"""

from __future__ import annotations

from typing import Final

from wm_dungeon_crawler.models import (
    Door,
    GameState,
    Grid,
    Guard,
    Item,
    Player,
    Position,
    TileType,
)

_WALL = "#"
_EXIT = "E"
_DOOR = "D"
_ITEM = "i"
_PLAYER = "P"
_FLOOR = "."


def parse_level(art: str) -> GameState:
    """Baut einen GameState aus einer mehrzeiligen ASCII-Beschreibung.

    Führende/nachgestellte Leerzeilen werden ignoriert, alle übrigen Zeilen
    müssen gleich lang sein. Der Rückgabewert enthält noch keine Gegner –
    die werden (mangels Patrouillenweg in der ASCII-Notation) separat
    hinzugefügt.

    >>> state = parse_level('''
    ... ###
    ... #P#
    ... #E#
    ... ###
    ... ''')
    >>> state.grid.width, state.grid.height
    (3, 4)
    >>> state.player.position
    Position(x=1, y=1)
    >>> state.grid.exit_position
    Position(x=1, y=2)
    """
    lines = [line for line in art.splitlines() if line.strip() != ""]
    if not lines:
        raise ValueError("Level-Beschreibung darf nicht leer sein")
    width = len(lines[0])
    if any(len(line) != width for line in lines):
        raise ValueError("Alle Zeilen einer Level-Beschreibung müssen gleich lang sein")
    height = len(lines)

    tiles: dict[Position, TileType] = {}
    doors: list[Door] = []
    items: list[Item] = []
    player_position: Position | None = None

    for y, line in enumerate(lines):
        for x, char in enumerate(line):
            position = Position(x, y)
            if char == _WALL:
                tiles[position] = TileType.WALL
            elif char == _EXIT:
                tiles[position] = TileType.EXIT
            elif char == _DOOR:
                doors.append(Door(position=position))
            elif char == _ITEM:
                items.append(Item(position=position, name="Trikot"))
            elif char == _PLAYER:
                player_position = position
            elif char != _FLOOR:
                raise ValueError(f"Unbekanntes Zeichen {char!r} in Level-Beschreibung")

    if player_position is None:
        raise ValueError("Level-Beschreibung enthält keine Startposition ('P')")

    grid = Grid(width=width, height=height, tiles=tiles)
    player = Player(position=player_position)
    return GameState(grid=grid, player=player, items=items, doors=doors)


FIXED_LEVEL_ART: Final[str] = """
#####
##P##
##.##
##.##
#i.##
##.##
##.##
#...#
#...#
##D##
##E##
#####
"""

_GUARD_PATROL_ROUTE: Final[list[Position]] = [
    Position(1, 7),
    Position(3, 7),
    Position(3, 8),
    Position(1, 8),
]


def create_fixed_level() -> GameState:
    """Erzeugt das eine feste, vollständig spielbare Level des Spiels.

    Der Weg führt vom Start durch einen schmalen Korridor, an dessen Rand in
    einer Nische ein Trikot liegt, an einem Raum vorbei, in dem eine
    Sicherheitskraft patrouilliert, bis zu einer verschlossenen Tür kurz vor
    dem Ausgang.

    >>> state = create_fixed_level()
    >>> state.grid.width, state.grid.height
    (5, 12)
    >>> len(state.guards)
    1
    >>> len(state.doors), len(state.items)
    (1, 1)
    """
    state = parse_level(FIXED_LEVEL_ART)
    state.guards.append(Guard(patrol_route=_GUARD_PATROL_ROUTE))
    return state
