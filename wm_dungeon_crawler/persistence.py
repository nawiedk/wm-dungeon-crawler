"""Speichern und Laden eines Spielstands als JSON, validiert mit Pydantic.

Die Dataclasses in `models.py` bilden den Live-Spielzustand ab; hier kommen
Pydantic-Gegenstücke dazu, die eigens für die Systemgrenze Datei <-> Programm
zuständig sind (Validierung + (De-)Serialisierung), so wie im Skript-Kapitel
zu Datenverarbeitung beschrieben: Pydantic validiert/konvertiert Daten an der
Systemgrenze, die interne Logik bleibt bei den Dataclasses. Jede Klasse hier
spiegelt daher eine Dataclass aus `models.py` eins zu eins.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field, ValidationError

from wm_dungeon_crawler.models import (
    MAX_STAMINA,
    Door,
    GameState,
    GameStatus,
    Grid,
    Guard,
    Item,
    Player,
    Position,
    TileType,
)

DEFAULT_SAVE_PATH: Path = Path("savegame.json")


class SaveFileError(Exception):
    """Die Speicherdatei fehlt oder enthält keinen gültigen Spielstand."""


class PositionData(BaseModel):
    """Pydantic-Gegenstück zu `models.Position`.

    >>> PositionData.from_position(Position(3, 4)).to_position()
    Position(x=3, y=4)
    """

    x: int
    y: int

    def to_position(self) -> Position:
        return Position(self.x, self.y)

    @classmethod
    def from_position(cls, position: Position) -> PositionData:
        return cls(x=position.x, y=position.y)


class TileData(BaseModel):
    """Ein einzelnes Rasterfeld mit nicht-Standard-Beschaffenheit (die
    übrigen Felder gelten laut `models.Grid` als FLOOR)."""

    position: PositionData
    tile_type: TileType


class GridData(BaseModel):
    """Pydantic-Gegenstück zu `models.Grid`."""

    width: int = Field(gt=0)
    height: int = Field(gt=0)
    tiles: list[TileData]

    def to_grid(self) -> Grid:
        return Grid(
            width=self.width,
            height=self.height,
            tiles={entry.position.to_position(): entry.tile_type for entry in self.tiles},
        )

    @classmethod
    def from_grid(cls, grid: Grid) -> GridData:
        return cls(
            width=grid.width,
            height=grid.height,
            tiles=[
                TileData(position=PositionData.from_position(position), tile_type=tile_type)
                for position, tile_type in grid.tiles.items()
            ],
        )


class DoorData(BaseModel):
    """Pydantic-Gegenstück zu `models.Door`."""

    position: PositionData
    locked: bool

    def to_door(self) -> Door:
        return Door(position=self.position.to_position(), locked=self.locked)

    @classmethod
    def from_door(cls, door: Door) -> DoorData:
        return cls(position=PositionData.from_position(door.position), locked=door.locked)


class ItemData(BaseModel):
    """Pydantic-Gegenstück zu `models.Item`."""

    position: PositionData
    name: str = Field(min_length=1)

    def to_item(self) -> Item:
        return Item(position=self.position.to_position(), name=self.name)

    @classmethod
    def from_item(cls, item: Item) -> ItemData:
        return cls(position=PositionData.from_position(item.position), name=item.name)


class PlayerData(BaseModel):
    """Pydantic-Gegenstück zu `models.Player`."""

    position: PositionData
    stamina: int = Field(ge=0, le=MAX_STAMINA)
    inventory: list[ItemData]

    def to_player(self) -> Player:
        return Player(
            position=self.position.to_position(),
            stamina=self.stamina,
            inventory=[item.to_item() for item in self.inventory],
        )

    @classmethod
    def from_player(cls, player: Player) -> PlayerData:
        return cls(
            position=PositionData.from_position(player.position),
            stamina=player.stamina,
            inventory=[ItemData.from_item(item) for item in player.inventory],
        )


class GuardData(BaseModel):
    """Pydantic-Gegenstück zu `models.Guard`."""

    patrol_route: list[PositionData] = Field(min_length=1)
    patrol_index: int = Field(ge=0)

    def to_guard(self) -> Guard:
        return Guard(
            patrol_route=[entry.to_position() for entry in self.patrol_route],
            patrol_index=self.patrol_index,
        )

    @classmethod
    def from_guard(cls, guard: Guard) -> GuardData:
        return cls(
            patrol_route=[PositionData.from_position(p) for p in guard.patrol_route],
            patrol_index=guard.patrol_index,
        )


class GameStateData(BaseModel):
    """Pydantic-Gegenstück zu `models.GameState`: das vollständige, aus
    einer Datei validierbare Speicherformat einer Partie."""

    grid: GridData
    player: PlayerData
    guards: list[GuardData]
    items: list[ItemData]
    doors: list[DoorData]
    status: GameStatus

    def to_game_state(self) -> GameState:
        return GameState(
            grid=self.grid.to_grid(),
            player=self.player.to_player(),
            guards=[guard.to_guard() for guard in self.guards],
            items=[item.to_item() for item in self.items],
            doors=[door.to_door() for door in self.doors],
            status=self.status,
        )

    @classmethod
    def from_game_state(cls, state: GameState) -> GameStateData:
        return cls(
            grid=GridData.from_grid(state.grid),
            player=PlayerData.from_player(state.player),
            guards=[GuardData.from_guard(guard) for guard in state.guards],
            items=[ItemData.from_item(item) for item in state.items],
            doors=[DoorData.from_door(door) for door in state.doors],
            status=state.status,
        )


def save_game(state: GameState, path: Path = DEFAULT_SAVE_PATH) -> None:
    """Speichert einen Spielzustand als validiertes JSON in eine Datei."""
    data = GameStateData.from_game_state(state)
    path.write_text(data.model_dump_json(indent=2), encoding="utf-8")


def load_game(path: Path = DEFAULT_SAVE_PATH) -> GameState:
    """Lädt und validiert einen Spielzustand aus einer JSON-Datei.

    Wirft `SaveFileError`, wenn die Datei fehlt oder ihr Inhalt kein
    gültiger Spielstand ist (z.B. manuell beschädigt).

    >>> import tempfile
    >>> from wm_dungeon_crawler.levels import create_fixed_level
    >>> state = create_fixed_level()
    >>> state.player.position = Position(2, 4)
    >>> with tempfile.TemporaryDirectory() as tmp:
    ...     save_path = Path(tmp) / "test_save.json"
    ...     save_game(state, save_path)
    ...     loaded = load_game(save_path)
    >>> loaded.player.position
    Position(x=2, y=4)
    >>> loaded.grid.width, loaded.grid.height
    (5, 12)
    >>> len(loaded.guards), len(loaded.doors), len(loaded.items)
    (1, 1, 1)
    >>> try:
    ...     load_game(Path("does_not_exist.json"))
    ... except SaveFileError as error:
    ...     print("Fehler:", error)
    Fehler: Keine Speicherdatei gefunden unter does_not_exist.json
    """
    try:
        raw = path.read_text(encoding="utf-8")
        data = GameStateData.model_validate_json(raw)
    except FileNotFoundError as error:
        raise SaveFileError(f"Keine Speicherdatei gefunden unter {path}") from error
    except ValidationError as error:
        raise SaveFileError(f"Speicherdatei ist ungültig: {error}") from error
    return data.to_game_state()
