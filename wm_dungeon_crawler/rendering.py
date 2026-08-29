"""Text-basierte Darstellung des Spielzustands.

Platzhalter für die spätere pygame-Oberfläche (Meilenstein 10). Kennt nur
Datenmodell und Level-Modul, keine Zug-/Bewegungslogik – rein lesend.
"""

from __future__ import annotations

from wm_dungeon_crawler.models import GameState, Position, TileType


def render_ascii(state: GameState) -> str:
    """Rendert den aktuellen Spielzustand als mehrzeiligen Text.

    Darstellung pro Feld (erster Treffer gewinnt): Spielfigur ``P``,
    Sicherheitskraft ``G``, Tür ``D`` (verschlossen) bzw. ``o`` (offen),
    Gegenstand ``i``, Wand ``#``, Ausgang ``E``, sonst begehbarer Boden ``.``.

    >>> from wm_dungeon_crawler.levels import create_fixed_level
    >>> print(render_ascii(create_fixed_level()))
    #####
    ##P##
    ##.##
    ##.##
    #i.##
    ##.##
    ##.##
    #G..#
    #...#
    ##D##
    ##E##
    #####
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
            elif grid.tile_at(position) is TileType.EXIT:
                row_chars.append("E")
            else:
                row_chars.append(".")
        rows.append("".join(row_chars))
    return "\n".join(rows)
