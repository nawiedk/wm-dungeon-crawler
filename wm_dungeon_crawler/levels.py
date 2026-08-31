"""Laden eines Levels aus einer ASCII-Beschreibung.

Level werden als mehrzeilige Zeichenkunst definiert und geparst. Das hält die
konkrete Level-Geometrie unabhängig davon, wie sie später dargestellt wird
(Text-Vorschau, pygame) – Trennung von Spiellogik und Darstellung.

Zeichen:
    '#'  Wand
    '.'  begehbarer Boden
    'F'  Fußballplatz (Feld) – nicht begehbar, nur optisch von der Wand
         unterschieden
    'B'  Barriere – dauerhaftes Hindernis, nicht begehbar, optisch von der
         Wand unterschieden (z.B. eine Absperrung statt einer Stadionmauer)
    'E'  Ausgang – ein Level kann mehrere haben (siehe
         `Grid.exit_positions`), jeder gewinnt die Partie
    'D'  verschlossene Tür (auf begehbarem Boden) – im festen Level nicht
         genutzt, die eine Tür des festen Levels wird in
         `create_fixed_level` platziert (siehe dort), bleibt aber als
         generisches Zeichen nutzbar
    'i'  Gegenstand (Schlüssel/Trikot, auf begehbarem Boden) – im festen
         Level nicht genutzt, das Trikot wird zufällig platziert (siehe
         `create_fixed_level`), bleibt aber als generisches Zeichen nutzbar
    'P'  Startposition der Spielfigur (auf begehbarem Boden)

Patrouillenwege von Sicherheitskräften lassen sich in einer einzelnen
Zeichenkunst nicht sinnvoll als geordnete Wegpunkte ausdrücken und werden
daher separat in Code angegeben, siehe `create_fixed_level`.
"""

from __future__ import annotations

import random
from typing import Final

from wm_dungeon_crawler.models import (
    Direction,
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
_PITCH = "F"
_BARRIER = "B"
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
    >>> state.grid.exit_positions
    {Position(x=1, y=2)}
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
            elif char == _PITCH:
                tiles[position] = TileType.PITCH
            elif char == _BARRIER:
                tiles[position] = TileType.BARRIER
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


def reachable_positions(
    grid: Grid, start: Position, doors: list[Door]
) -> set[Position]:
    """Ermittelt alle von `start` aus erreichbaren begehbaren Felder.

    Verschlossene Türen gelten dabei als (vorübergehend) unpassierbar –
    genau wie bei der tatsächlichen Bewegung in `Engine.is_passable`.

    >>> grid = Grid(width=3, height=1)
    >>> sorted(reachable_positions(grid, Position(0, 0), doors=[]))
    [Position(x=0, y=0), Position(x=1, y=0), Position(x=2, y=0)]
    >>> door = Door(position=Position(1, 0))
    >>> sorted(reachable_positions(grid, Position(0, 0), doors=[door]))
    [Position(x=0, y=0)]
    """
    blocked = {door.position for door in doors if door.locked}
    visited = {start}
    frontier = [start]
    while frontier:
        current = frontier.pop()
        for direction in Direction:
            neighbor = current + direction
            if neighbor in visited or neighbor in blocked:
                continue
            if not grid.is_walkable(neighbor):
                continue
            visited.add(neighbor)
            frontier.append(neighbor)
    return visited


FIXED_LEVEL_ART: Final[str] = """
###########
#.........#
#.........#
#.P.......#
#...FFF...#
#...FFF...#
#...FFF##E#
#...FFF..B#
#...FFF...#
#....B....#
#.........#
#....B....#
########E##
"""

_GUARD_PATROL_ROUTE: Final[list[Position]] = [
    Position(2, 2),
    Position(3, 2),
    Position(4, 2),
    Position(5, 2),
    Position(6, 2),
    Position(7, 2),
    Position(8, 2),
    Position(7, 2),
    Position(6, 2),
    Position(5, 2),
    Position(4, 2),
    Position(3, 2),
]


def create_fixed_level() -> GameState:
    """Erzeugt das eine feste, vollständig spielbare Level des Spiels.

    Drei Felder breite Stadiongänge umschließen den Fußballplatz
    (`TileType.PITCH`, nicht begehbar) – O-förmig, wie ein echtes Stadion.
    Eine Barriere (`TileType.BARRIER`) blockiert an einer Stelle zwei der
    drei Gang-Spuren dauerhaft, die mittlere bleibt als Durchgang offen –
    der Ring bleibt also insgesamt eine geschlossene Schleife. Es gibt
    zwei gleichwertige Ausgänge (`Grid.exit_positions`), zwischen denen
    frei gewählt werden kann: der bei (9, 6) ist von Anfang an offen,
    liegt aber nah an der Patrouille der Sicherheitskraft – der riskante,
    direkte Weg (eine zweite Barriere direkt dahinter ist rein optisch;
    da das Erreichen dieses Ausgangs die Partie sofort gewinnt, spielt es
    keine Rolle, dass dahinter ohnehin nichts weiter erreichbar wäre).
    Der zweite liegt unten auf der gegenüberliegenden Seite
    und sitzt hinter einer Tür, die sich erst nach dem Einsammeln des
    Trikots öffnet – der sicherere, aber weitere Weg. Das Trikot spawnt
    zufällig auf einem regulären Bodenfeld (nicht auf Rasen, Wand,
    Barriere, einer Tür oder einem Ausgang), garantiert aber vom Start
    aus erreichbar (sonst gäbe es ein unlösbares Level).

    >>> state = create_fixed_level()
    >>> state.grid.width, state.grid.height
    (11, 13)
    >>> len(state.guards)
    1
    >>> len(state.doors), len(state.items)
    (1, 1)
    >>> len(state.grid.exit_positions)
    2
    """
    state = parse_level(FIXED_LEVEL_ART)
    state.guards.append(Guard(patrol_route=_GUARD_PATROL_ROUTE))
    state.doors.append(Door(position=Position(8, 12), locked=True))

    door_positions = {door.position for door in state.doors}
    candidates = reachable_positions(state.grid, state.player.position, state.doors)
    candidates.discard(state.player.position)
    candidates.difference_update(guard.position for guard in state.guards)
    candidates = {
        position
        for position in candidates
        if state.grid.tile_at(position) is TileType.FLOOR
        and position not in door_positions
    }
    state.items.append(Item(position=random.choice(list(candidates)), name="Trikot"))

    return state
