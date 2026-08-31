"""Text-basierte Darstellung des Spielzustands.

Platzhalter/schnelle Alternative zur pygame-Oberfläche (`gui.py`). Kennt nur
Datenmodell und Level-Modul, keine Zug-/Bewegungslogik – rein lesend.
"""

from __future__ import annotations

from wm_dungeon_crawler.models import GameState, Position, TileType


def render_ascii(state: GameState) -> str:
    """Rendert den aktuellen Spielzustand als mehrzeiligen Text.

    Darstellung pro Feld (erster Treffer gewinnt): Spielfigur ``P``,
    Sicherheitskraft ``G``, Tür ``D`` (verschlossen) bzw. ``o`` (offen),
    Gegenstand ``i``, Wand ``#``, Fußballplatz ``F``, Barriere ``B``,
    Ausgang ``E``, sonst begehbarer Boden ``.``.

    Nutzt hier bewusst einen kleinen, selbst gebauten Zustand statt
    `create_fixed_level()` – das feste Level platziert das Trikot seit
    Kurzem zufällig, ein Doctest darf aber nicht vom Zufall abhängen.

    >>> from wm_dungeon_crawler.models import (
    ...     Door, Grid, Guard, Item, Player,
    ... )
    >>> grid = Grid(
    ...     width=8,
    ...     height=1,
    ...     tiles={
    ...         Position(2, 0): TileType.PITCH,
    ...         Position(3, 0): TileType.BARRIER,
    ...         Position(7, 0): TileType.EXIT,
    ...     },
    ... )
    >>> state = GameState(
    ...     grid=grid,
    ...     player=Player(position=Position(0, 0)),
    ...     items=[Item(position=Position(4, 0), name="Trikot")],
    ...     doors=[Door(position=Position(5, 0))],
    ...     guards=[Guard(patrol_route=[Position(6, 0)])],
    ... )
    >>> render_ascii(state)
    'P.FBiDGE'
    """
    grid = state.grid
    door_by_position = {door.position: door for door in state.doors}
    item_positions = {item.position for item in state.items}
    guard_positions = {guard.position for guard in state.guards}

    rows: list[str] = []
    for y in range(grid.height):
        row_chars: list[str] = []
        for x in range(grid.width):
            position = Position(x, y)
            if position == state.player.position:
                row_chars.append("P")
            elif position in guard_positions:
                row_chars.append("G")
            elif position in door_by_position:
                row_chars.append("D" if door_by_position[position].locked else "o")
            elif position in item_positions:
                row_chars.append("i")
            elif grid.tile_at(position) is TileType.WALL:
                row_chars.append("#")
            elif grid.tile_at(position) is TileType.PITCH:
                row_chars.append("F")
            elif grid.tile_at(position) is TileType.BARRIER:
                row_chars.append("B")
            elif grid.tile_at(position) is TileType.EXIT:
                row_chars.append("E")
            else:
                row_chars.append(".")
        rows.append("".join(row_chars))
    return "\n".join(rows)
