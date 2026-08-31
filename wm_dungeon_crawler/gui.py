"""Grafische Oberfläche mit pygame.

Ergänzt die Text-Vorschau aus `rendering.py` (die bewusst erhalten bleibt –
schnell, ohne Fenster testbar, von den Doctests/CI mitgeprüft) um eine
echte grafische Darstellung samt Steuerung. Kennt nur Datenmodell, `Engine`,
`persistence` und `highscores`, keine eigene Spiellogik.

Alle Grafiken sind Pixelart-Bilddateien unter `assets/` (von der Nutzerin
per KI-Bildgenerator erstellt), keine selbst gezeichneten Formen. Der
Ausgang nutzt dieselbe Grafik wie eine offene Tür (`door_unlocked.png`) –
dafür gibt es keine eigene `exit`-Datei. Das Trikot-Icon schwebt leicht
auf und ab (siehe `_jersey_bob_offset`), alle übrigen Grafiken stehen fest.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import pygame

from wm_dungeon_crawler.engine import Engine
from wm_dungeon_crawler.highscores import load_highscores, record_attempt
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

ASSETS_DIR = Path(__file__).parent / "assets"
PIXEL_ART_BASE = 32
_BG_STRIP_SIZE = 128
_BG_TOLERANCE = 24

TILE_SIZE = 64
ENTITY_SCALE = 0.85
PANEL_WIDTH = 260
MARGIN = 16

_JERSEY_BOB_AMPLITUDE = 6
_JERSEY_BOB_PERIOD_MS = 1200

COLOR_BACKGROUND = (20, 20, 24)
COLOR_PITCH_LINE = (225, 230, 220)
COLOR_WON_TEXT = (90, 200, 110)
COLOR_ALERT = (210, 60, 60)
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


@dataclass
class Sprites:
    """Alle geladenen, bereits passend skalierten Pixelart-Grafiken."""

    wall: pygame.Surface
    floor: pygame.Surface
    pitch: pygame.Surface
    barrier: pygame.Surface
    door_locked: pygame.Surface
    door_unlocked: pygame.Surface
    player: pygame.Surface
    player_jersey: pygame.Surface
    guard: pygame.Surface
    jersey: pygame.Surface


def _pixelate(surface: pygame.Surface, size: int) -> pygame.Surface:
    """Rastert eine Surface auf einen scharfen Pixel-Look in `size`×`size`.

    Erst weich auf `PIXEL_ART_BASE` herunterskaliert (mittelt Unschärfen aus
    der KI-Generierung heraus), dann hart (ohne Glättung) hochskaliert,
    damit gleichmäßig scharfe Pixelkanten entstehen.
    """
    small = pygame.transform.smoothscale(surface, (PIXEL_ART_BASE, PIXEL_ART_BASE))
    return pygame.transform.scale(small, (size, size))


def _strip_background_and_crop(surface: pygame.Surface) -> pygame.Surface:
    """Macht eine (angenommen: einfarbige) Hintergrundfarbe transparent und
    schneidet auf den verbleibenden Bildinhalt zu.

    Die Hintergrundfarbe wird aus der linken oberen Ecke abgelesen – KI-
    generierte Icons liefern typischerweise keinen echten Alphakanal,
    sondern einen einfarbigen (meist weißen) Hintergrund.
    """
    surface = surface.convert_alpha()
    width, height = surface.get_size()
    bg = surface.get_at((0, 0))

    min_x, min_y, max_x, max_y = width, height, -1, -1
    for x in range(width):
        for y in range(height):
            r, g, b, _a = surface.get_at((x, y))
            if (
                abs(r - bg.r) <= _BG_TOLERANCE
                and abs(g - bg.g) <= _BG_TOLERANCE
                and abs(b - bg.b) <= _BG_TOLERANCE
            ):
                surface.set_at((x, y), (r, g, b, 0))
            else:
                min_x, min_y = min(min_x, x), min(min_y, y)
                max_x, max_y = max(max_x, x), max(max_y, y)

    if max_x < min_x or max_y < min_y:
        return surface
    bounds = pygame.Rect(min_x, min_y, max_x - min_x + 1, max_y - min_y + 1)
    return surface.subsurface(bounds).copy()


def _fit_to_square(surface: pygame.Surface, size: int) -> pygame.Surface:
    """Skaliert eine Surface seitenverhältnis-treu in ein `size`×`size`
    Quadrat mit transparentem Rand (statt sie zu verzerren)."""
    width, height = surface.get_size()
    scale = size / max(width, height)
    new_width = max(1, round(width * scale))
    new_height = max(1, round(height * scale))
    scaled = pygame.transform.smoothscale(surface, (new_width, new_height))

    canvas = pygame.Surface((size, size), pygame.SRCALPHA)
    canvas.blit(scaled, ((size - new_width) // 2, (size - new_height) // 2))
    return canvas


def _load_texture_sprite(filename: str, size: int) -> pygame.Surface:
    """Lädt eine deckende Kachel-Textur (Boden/Wand/Rasen) ohne Zuschnitt."""
    image = pygame.image.load(ASSETS_DIR / filename).convert_alpha()
    return _pixelate(image, size)


def _load_icon_sprite(filename: str, size: int) -> pygame.Surface:
    """Lädt ein freigestelltes Icon (Figur/Gegenstand/Tür).

    Hintergrund entfernen, auf den Bildinhalt zuschneiden, seitenverhältnis-
    treu einpassen, dann pixeln.
    """
    image = pygame.image.load(ASSETS_DIR / filename).convert_alpha()
    shrunk = pygame.transform.smoothscale(image, (_BG_STRIP_SIZE, _BG_STRIP_SIZE))
    cropped = _strip_background_and_crop(shrunk)
    fitted = _fit_to_square(cropped, PIXEL_ART_BASE)
    return pygame.transform.scale(fitted, (size, size))


def _load_sprites() -> Sprites:
    """Lädt alle Assets aus `assets/` in Kachel- bzw. Figurengröße."""
    entity_size = round(TILE_SIZE * ENTITY_SCALE)
    return Sprites(
        wall=_load_texture_sprite("wall.png", TILE_SIZE),
        floor=_load_texture_sprite("floor.png", TILE_SIZE),
        pitch=_load_texture_sprite("pitch.png", TILE_SIZE),
        barrier=_load_texture_sprite("barrier.png", TILE_SIZE),
        door_locked=_load_icon_sprite("door_locked.png", TILE_SIZE),
        door_unlocked=_load_icon_sprite("door_unlocked.png", TILE_SIZE),
        player=_load_icon_sprite("player.png", entity_size),
        player_jersey=_load_icon_sprite("player_jersey.png", entity_size),
        guard=_load_icon_sprite("guard.png", entity_size),
        jersey=_load_icon_sprite("jersey.png", entity_size),
    )


def _tile_sprite(tile_type: TileType, sprites: Sprites) -> pygame.Surface:
    """Wählt die Kachelgrafik für einen Feldtyp (Ausgang = offene Tür)."""
    if tile_type is TileType.WALL:
        return sprites.wall
    if tile_type is TileType.PITCH:
        return sprites.pitch
    if tile_type is TileType.BARRIER:
        return sprites.barrier
    if tile_type is TileType.EXIT:
        return sprites.door_unlocked
    return sprites.floor


def _jersey_bob_offset() -> int:
    """Berechnet den aktuellen vertikalen Schwebe-Versatz des Trikot-Icons.

    Sinusförmig über der Spielzeit (`pygame.time.get_ticks`), damit das
    Trikot gleichmäßig auf und ab schwebt statt starr auf der Kachel zu
    liegen.
    """
    phase = (pygame.time.get_ticks() % _JERSEY_BOB_PERIOD_MS) / _JERSEY_BOB_PERIOD_MS
    return round(_JERSEY_BOB_AMPLITUDE * math.sin(phase * 2 * math.pi))


def _blit_centered(
    surface: pygame.Surface, sprite: pygame.Surface, center: tuple[int, int]
) -> None:
    """Zeichnet ein Sprite so, dass es auf `center` zentriert ist."""
    surface.blit(sprite, sprite.get_rect(center=center))


def _draw_pitch_markings(surface: pygame.Surface, state: GameState) -> None:
    """Zeichnet eine schlichte Mittellinie und einen Anstoßkreis auf den
    Fußballplatz in der Mitte des Levels (rein dekorativ, oben auf der
    Rasen-Textur)."""
    pitch_positions = [
        position
        for position, tile_type in state.grid.tiles.items()
        if tile_type is TileType.PITCH
    ]
    if not pitch_positions:
        return

    left = MARGIN + min(p.x for p in pitch_positions) * TILE_SIZE
    top = MARGIN + min(p.y for p in pitch_positions) * TILE_SIZE
    right = MARGIN + (max(p.x for p in pitch_positions) + 1) * TILE_SIZE
    bottom = MARGIN + (max(p.y for p in pitch_positions) + 1) * TILE_SIZE
    center = ((left + right) // 2, (top + bottom) // 2)

    pygame.draw.line(
        surface, COLOR_PITCH_LINE, (left, center[1]), (right, center[1]), 2
    )
    radius = min(right - left, bottom - top) // 4
    pygame.draw.circle(surface, COLOR_PITCH_LINE, center, radius, width=2)


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
    surface: pygame.Surface,
    state: GameState,
    sprites: Sprites,
    font: pygame.font.Font,
    message: str = "",
) -> None:
    """Zeichnet den aktuellen Spielzustand auf die gegebene Surface."""
    surface.fill(COLOR_BACKGROUND)

    door_by_position = {door.position: door for door in state.doors}
    item_positions = {item.position for item in state.items}
    guard_positions = {guard.position for guard in state.guards}
    has_jersey = any(item.name == "Trikot" for item in state.player.inventory)
    jersey_bob = _jersey_bob_offset()

    for y in range(state.grid.height):
        for x in range(state.grid.width):
            position = Position(x, y)
            top_left = (MARGIN + x * TILE_SIZE, MARGIN + y * TILE_SIZE)

            door = door_by_position.get(position)
            tile_sprite = (
                (sprites.door_locked if door.locked else sprites.door_unlocked)
                if door is not None
                else _tile_sprite(state.grid.tile_at(position), sprites)
            )
            surface.blit(tile_sprite, top_left)

            center = (top_left[0] + TILE_SIZE // 2, top_left[1] + TILE_SIZE // 2)
            if position in item_positions:
                jersey_center = (center[0], center[1] + jersey_bob)
                _blit_centered(surface, sprites.jersey, jersey_center)
            if position in guard_positions:
                _blit_centered(surface, sprites.guard, center)
            if position == state.player.position:
                player_sprite = sprites.player_jersey if has_jersey else sprites.player
                _blit_centered(surface, player_sprite, center)

    _draw_pitch_markings(surface, state)
    _draw_panel(surface, state, font, message)


def _draw_panel(
    surface: pygame.Surface, state: GameState, font: pygame.font.Font, message: str
) -> None:
    """Zeichnet Ausdauer, Inventar, Rundenzahl, Steuerungs-Übersicht und
    Statusmeldung."""
    panel_x = MARGIN * 2 + state.grid.width * TILE_SIZE
    panel_text_width = PANEL_WIDTH - MARGIN
    inventory = ", ".join(item.name for item in state.player.inventory) or "leer"
    lines = [
        f"Ausdauer: {state.player.stamina}/{MAX_STAMINA}",
        f"Inventar: {inventory}",
        f"Runden: {state.turns_taken}",
        "",
        "Pfeiltasten/WASD: gehen",
        "+ Shift: sprinten",
        "R: ausruhen",
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
    surface: pygame.Surface,
    state: GameState,
    font: pygame.font.Font,
    font_large: pygame.font.Font,
) -> None:
    """Zeichnet eine abgedunkelte Sieg-/Niederlage-Meldung über dem Raster,
    bei einem Sieg zusätzlich benötigte Runden und Bestenliste."""
    if state.status is GameStatus.WON:
        text, color = "Gewonnen! Frankreich schmeisst Paraguay raus.", COLOR_WON_TEXT
    elif state.status is GameStatus.LOST:
        text, color = "Verloren! Paraguay schmeisst Deutschland raus.", COLOR_ALERT
    else:
        return

    grid_width_px = state.grid.width * TILE_SIZE
    grid_height_px = state.grid.height * TILE_SIZE
    overlay = pygame.Surface((grid_width_px, grid_height_px), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 180))
    surface.blit(overlay, (MARGIN, MARGIN))

    center_x = MARGIN + grid_width_px // 2
    center_y = MARGIN + grid_height_px // 2
    rendered = font_large.render(text, True, color)
    rect = rendered.get_rect(center=(center_x, center_y))
    surface.blit(rendered, rect)

    if state.status is GameStatus.WON:
        _draw_highscore_lines(surface, state, font, center_x, rect.bottom)


def _draw_highscore_lines(
    surface: pygame.Surface,
    state: GameState,
    font: pygame.font.Font,
    center_x: int,
    top: int,
) -> None:
    """Zeigt die für diesen Sieg benötigten Runden sowie die Bestenliste
    (wenigste Runden zuerst) unter der Siegmeldung an."""
    highscores = load_highscores()
    lines = [
        f"Runden benötigt: {state.turns_taken}",
        f"Bestenliste: {', '.join(str(turns) for turns in highscores)}",
    ]
    for row, line in enumerate(lines):
        rendered = font.render(line, True, COLOR_TEXT)
        rect = rendered.get_rect(center=(center_x, top + 28 + row * 24))
        surface.blit(rendered, rect)


def _record_highscore_if_won(state: GameState) -> None:
    """Trägt bei einem frischen Sieg die benötigten Runden in die
    Bestenliste ein.

    Wird direkt nach einem erfolgreichen Zug aufgerufen. Da nach einem Sieg
    keine weiteren Züge mehr möglich sind (siehe `_handle_keydown`), passiert
    das dadurch garantiert nur einmal pro Partie.
    """
    if state.status is GameStatus.WON:
        record_attempt(state.turns_taken)


def _handle_keydown(engine: Engine, event: pygame.event.Event) -> str | None:
    """Verarbeitet einen Tastendruck als einen Spielzug (Bewegung/Ausruhen;
    Speichern/Laden/Beenden übernimmt die Hauptschleife). Verschlossene
    Türen öffnen sich automatisch beim Einsammeln eines Gegenstands, dafür
    gibt es keine eigene Taste.

    Gibt `None` zurück, wenn die Taste keine Spielaktion war (Statusmeldung
    bleibt unverändert), sonst eine neue Meldung – leer, wenn die Aktion
    erfolgreich war (löscht eine evtl. alte Fehlermeldung).
    """
    if engine.state.status is not GameStatus.PLAYING:
        return None

    if event.key == pygame.K_r:
        engine.take_turn_rest()
        _record_highscore_if_won(engine.state)
        return ""

    direction = _DIRECTION_KEYS.get(event.key)
    if direction is None:
        return None

    sprint = bool(event.mod & pygame.KMOD_SHIFT)
    if engine.take_turn_move(direction, sprint=sprint):
        _record_highscore_if_won(engine.state)
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
    sprites = _load_sprites()
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

        draw_state(screen, engine.state, sprites, font, message)
        _draw_end_overlay(screen, engine.state, font, font_large)
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()


if __name__ == "__main__":
    main()
