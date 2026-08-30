"""Grafische Oberfläche mit pygame.

Ergänzt die Text-Vorschau aus `rendering.py` (die bewusst erhalten bleibt –
schnell, ohne Fenster testbar, von den Doctests/CI mitgeprüft) um eine
echte grafische Darstellung samt Steuerung. Kennt nur Datenmodell, `Engine`
und `persistence`, keine eigene Spiellogik.
"""

from __future__ import annotations

import pygame

from wm_dungeon_crawler.engine import Engine
from wm_dungeon_crawler.levels import create_fixed_level
from wm_dungeon_crawler.models import (
    MAX_STAMINA,
    Direction,
    GameState,
    GameStatus,
    Position,
    TileType,
)
from wm_dungeon_crawler.persistence import SaveFileError, load_game, save_game

TILE_SIZE = 48
PANEL_WIDTH = 260
MARGIN = 16

COLOR_BACKGROUND = (20, 20, 24)
COLOR_WALL = (60, 60, 68)
COLOR_FLOOR = (150, 150, 158)
COLOR_EXIT = (70, 170, 90)
COLOR_DOOR_LOCKED = (150, 90, 40)
COLOR_DOOR_UNLOCKED = (110, 150, 110)
COLOR_ITEM = (230, 190, 40)
COLOR_PLAYER = (60, 120, 220)
COLOR_GUARD = (200, 50, 50)
COLOR_TEXT = (230, 230, 230)

_DIRECTION_KEYS: dict[int, Direction] = {
    pygame.K_UP: Direction.UP,
    pygame.K_w: Direction.UP,
    pygame.K_DOWN: Direction.DOWN,
    pygame.K_s: Direction.DOWN,
    pygame.K_LEFT: Direction.LEFT,
    pygame.K_a: Direction.LEFT,
    pygame.K_RIGHT: Direction.RIGHT,
    pygame.K_d: Direction.RIGHT,
}


def _tile_color(tile_type: TileType) -> tuple[int, int, int]:
    """Hintergrundfarbe eines Rasterfelds ohne besonderen Belag (Tür)."""
    if tile_type is TileType.WALL:
        return COLOR_WALL
    if tile_type is TileType.EXIT:
        return COLOR_EXIT
    return COLOR_FLOOR


def _wrap_text(text: str, font: pygame.font.Font, max_width: int) -> list[str]:
    """Bricht einen Text in Zeilen um, die höchstens max_width Pixel breit sind."""
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if font.size(candidate)[0] <= max_width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_state(
    surface: pygame.Surface, state: GameState, font: pygame.font.Font, message: str = ""
) -> None:
    """Zeichnet den aktuellen Spielzustand auf die gegebene Surface."""
    surface.fill(COLOR_BACKGROUND)

    door_by_position = {door.position: door for door in state.doors}
    item_positions = {item.position for item in state.items}
    guard_positions = {guard.position for guard in state.guards}

    for y in range(state.grid.height):
        for x in range(state.grid.width):
            position = Position(x, y)
            rect = pygame.Rect(
                MARGIN + x * TILE_SIZE, MARGIN + y * TILE_SIZE, TILE_SIZE, TILE_SIZE
            )

            door = door_by_position.get(position)
            color = (
                (COLOR_DOOR_LOCKED if door.locked else COLOR_DOOR_UNLOCKED)
                if door is not None
                else _tile_color(state.grid.tile_at(position))
            )
            pygame.draw.rect(surface, color, rect)
            pygame.draw.rect(surface, COLOR_BACKGROUND, rect, width=1)

            center = rect.center
            if position in item_positions:
                pygame.draw.circle(surface, COLOR_ITEM, center, TILE_SIZE // 5)
            if position in guard_positions:
                pygame.draw.circle(surface, COLOR_GUARD, center, TILE_SIZE // 3)
            if position == state.player.position:
                pygame.draw.circle(surface, COLOR_PLAYER, center, TILE_SIZE // 3)

    _draw_panel(surface, state, font, message)


def _draw_panel(
    surface: pygame.Surface, state: GameState, font: pygame.font.Font, message: str
) -> None:
    """Zeichnet Ausdauer, Inventar, Steuerungs-Übersicht und Statusmeldung."""
    panel_x = MARGIN * 2 + state.grid.width * TILE_SIZE
    panel_text_width = PANEL_WIDTH - MARGIN
    inventory = ", ".join(item.name for item in state.player.inventory) or "leer"
    lines = [
        f"Ausdauer: {state.player.stamina}/{MAX_STAMINA}",
        f"Inventar: {inventory}",
        "",
        "Pfeiltasten/WASD: gehen",
        "+ Shift: sprinten",
        "R: ausruhen",
        "U: Tür aufschließen",
        "F5: speichern  F9: laden",
        "Esc: beenden",
    ]
    if message:
        lines.append("")
        lines.extend(_wrap_text(message, font, panel_text_width))

    for row, text in enumerate(lines):
        rendered = font.render(text, True, COLOR_TEXT)
        surface.blit(rendered, (panel_x, MARGIN + row * 24))


def _draw_end_overlay(
    surface: pygame.Surface, state: GameState, font_large: pygame.font.Font
) -> None:
    """Zeichnet eine abgedunkelte Sieg-/Niederlage-Meldung über dem Raster."""
    if state.status is GameStatus.WON:
        text, color = "Geschafft! Gewonnen!", COLOR_EXIT
    elif state.status is GameStatus.LOST:
        text, color = "Erwischt! Game Over.", COLOR_GUARD
    else:
        return

    grid_width_px = state.grid.width * TILE_SIZE
    grid_height_px = state.grid.height * TILE_SIZE
    overlay = pygame.Surface((grid_width_px, grid_height_px), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (MARGIN, MARGIN))

    rendered = font_large.render(text, True, color)
    rect = rendered.get_rect(
        center=(MARGIN + grid_width_px // 2, MARGIN + grid_height_px // 2)
    )
    surface.blit(rendered, rect)


def _handle_keydown(engine: Engine, event: pygame.event.Event) -> str | None:
    """Verarbeitet einen Tastendruck als einen Spielzug (Bewegung/Ausruhen/
    Aufschließen; Speichern/Laden/Beenden übernimmt die Hauptschleife).

    Gibt `None` zurück, wenn die Taste keine Spielaktion war (Statusmeldung
    bleibt unverändert), sonst eine neue Meldung – leer, wenn die Aktion
    erfolgreich war (löscht eine evtl. alte Fehlermeldung).
    """
    if engine.state.status is not GameStatus.PLAYING:
        return None

    if event.key == pygame.K_r:
        engine.take_turn_rest()
        return ""
    if event.key == pygame.K_u:
        if engine.try_unlock_adjacent_door():
            return ""
        return (
            "Das geht nicht - keine angrenzende Tür oder kein Gegenstand im Inventar."
        )

    direction = _DIRECTION_KEYS.get(event.key)
    if direction is None:
        return None

    sprint = bool(event.mod & pygame.KMOD_SHIFT)
    if engine.take_turn_move(direction, sprint=sprint):
        return ""
    return "Das geht nicht - zu wenig Ausdauer oder der Weg ist versperrt."


def main() -> None:
    """Öffnet das Fenster, verarbeitet Eingaben und zeigt Sieg/Niederlage."""
    engine = Engine(create_fixed_level())
    message = ""

    pygame.init()
    window_width = MARGIN * 3 + engine.state.grid.width * TILE_SIZE + PANEL_WIDTH
    window_height = MARGIN * 2 + engine.state.grid.height * TILE_SIZE
    screen = pygame.display.set_mode((window_width, window_height))
    pygame.display.set_caption("WM-Dungeon-Crawler")
    font = pygame.font.SysFont(None, 22)
    font_large = pygame.font.SysFont(None, 40)
    clock = pygame.time.Clock()

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_F5:
                    save_game(engine.state)
                    message = "Spielstand gespeichert."
                elif event.key == pygame.K_F9:
                    try:
                        engine.state = load_game()
                        message = "Spielstand geladen."
                    except SaveFileError as error:
                        message = f"Laden fehlgeschlagen: {error}"
                else:
                    result = _handle_keydown(engine, event)
                    if result is not None:
                        message = result

        draw_state(screen, engine.state, font, message)
        _draw_end_overlay(screen, engine.state, font_large)
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()
