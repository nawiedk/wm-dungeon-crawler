"""Tests für die Spiellogik in wm_dungeon_crawler.engine."""

from hypothesis import given
from hypothesis import strategies as st

from wm_dungeon_crawler.engine import Engine
from wm_dungeon_crawler.models import (
    MAX_STAMINA,
    Direction,
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


def test_move_blocked_by_wall_has_no_side_effects() -> None:
    grid = Grid(width=3, height=1, tiles={Position(2, 0): TileType.WALL})
    state = GameState(grid=grid, player=Player(position=Position(1, 0)))
    engine = Engine(state)

    assert engine.take_turn_move(Direction.RIGHT) is False
    assert engine.state.player.position == Position(1, 0)
    assert engine.state.player.stamina == MAX_STAMINA
    assert engine.state.turns_taken == 0


def test_move_onto_open_floor_succeeds() -> None:
    grid = Grid(width=3, height=1)
    state = GameState(grid=grid, player=Player(position=Position(1, 0)))
    engine = Engine(state)

    assert engine.take_turn_move(Direction.RIGHT) is True
    assert engine.state.player.position == Position(2, 0)


def test_cannot_walk_onto_pitch() -> None:
    grid = Grid(width=3, height=1, tiles={Position(1, 0): TileType.PITCH})
    state = GameState(grid=grid, player=Player(position=Position(0, 0)))
    engine = Engine(state)

    assert engine.take_turn_move(Direction.RIGHT) is False
    assert engine.state.player.position == Position(0, 0)


def test_sprint_collects_item_on_intermediate_tile() -> None:
    grid = Grid(width=3, height=1)
    item = Item(position=Position(1, 0), name="Schlüssel")
    state = GameState(grid=grid, player=Player(position=Position(0, 0)), items=[item])
    engine = Engine(state)

    assert engine.take_turn_move(Direction.RIGHT, sprint=True) is True
    assert engine.state.player.position == Position(2, 0)
    assert engine.state.items == []
    assert [collected.name for collected in engine.state.player.inventory] == [
        "Schlüssel"
    ]


def test_sprint_blocked_on_second_tile_has_no_side_effects() -> None:
    grid = Grid(width=3, height=1, tiles={Position(2, 0): TileType.WALL})
    state = GameState(grid=grid, player=Player(position=Position(0, 0)))
    engine = Engine(state)

    assert engine.take_turn_move(Direction.RIGHT, sprint=True) is False
    assert engine.state.player.position == Position(0, 0)
    assert engine.state.player.stamina == MAX_STAMINA
    assert engine.state.turns_taken == 0


def test_collecting_item_automatically_unlocks_all_doors() -> None:
    grid = Grid(width=3, height=1)
    item = Item(position=Position(1, 0), name="Trikot")
    door = Door(position=Position(2, 0))
    state = GameState(
        grid=grid, player=Player(position=Position(0, 0)), items=[item], doors=[door]
    )
    engine = Engine(state)

    assert engine.take_turn_move(Direction.RIGHT) is True
    assert door.locked is False
    assert [collected.name for collected in engine.state.player.inventory] == ["Trikot"]


def test_collecting_item_unlocks_every_locked_door() -> None:
    grid = Grid(width=4, height=1)
    item = Item(position=Position(1, 0), name="Trikot")
    door_a = Door(position=Position(2, 0))
    door_b = Door(position=Position(3, 0))
    state = GameState(
        grid=grid,
        player=Player(position=Position(0, 0)),
        items=[item],
        doors=[door_a, door_b],
    )
    engine = Engine(state)

    assert engine.take_turn_move(Direction.RIGHT) is True
    assert door_a.locked is False
    assert door_b.locked is False


def test_player_walking_into_guard_is_caught() -> None:
    grid = Grid(width=3, height=1)
    guard = Guard(patrol_route=[Position(1, 0)])
    state = GameState(grid=grid, player=Player(position=Position(0, 0)), guards=[guard])
    engine = Engine(state)

    engine.take_turn_move(Direction.RIGHT)
    assert engine.state.status is GameStatus.LOST


def test_guard_walking_into_resting_player_is_caught() -> None:
    grid = Grid(width=3, height=1)
    guard = Guard(patrol_route=[Position(0, 0), Position(1, 0)])
    state = GameState(grid=grid, player=Player(position=Position(1, 0)), guards=[guard])
    engine = Engine(state)

    engine.take_turn_rest()
    assert engine.state.status is GameStatus.LOST


def test_reaching_exit_wins() -> None:
    grid = Grid(width=2, height=1, tiles={Position(1, 0): TileType.EXIT})
    state = GameState(grid=grid, player=Player(position=Position(0, 0)))
    engine = Engine(state)

    assert engine.take_turn_move(Direction.RIGHT) is True
    assert engine.state.status is GameStatus.WON


def test_winning_takes_priority_over_being_caught_on_the_same_move() -> None:
    grid = Grid(width=2, height=1, tiles={Position(1, 0): TileType.EXIT})
    guard = Guard(patrol_route=[Position(1, 0)])
    state = GameState(grid=grid, player=Player(position=Position(0, 0)), guards=[guard])
    engine = Engine(state)

    engine.take_turn_move(Direction.RIGHT)
    assert engine.state.status is GameStatus.WON


def test_no_action_possible_after_losing() -> None:
    grid = Grid(width=4, height=1)
    guard = Guard(patrol_route=[Position(2, 0)])
    player = Player(position=Position(0, 0))
    state = GameState(
        grid=grid, player=player, guards=[guard], doors=[Door(position=Position(3, 0))]
    )
    engine = Engine(state)

    engine.take_turn_move(Direction.RIGHT, sprint=True)
    assert engine.state.status is GameStatus.LOST
    assert engine.state.player.stamina == 0
    assert engine.state.turns_taken == 1

    assert engine.take_turn_move(Direction.LEFT) is False
    assert engine.state.player.position == Position(2, 0)
    assert engine.state.turns_taken == 1

    engine.take_turn_rest()
    assert engine.state.player.stamina == 0
    assert engine.state.turns_taken == 1


def test_turns_taken_increments_on_move_and_rest() -> None:
    grid = Grid(width=3, height=1)
    state = GameState(grid=grid, player=Player(position=Position(1, 0)))
    engine = Engine(state)

    assert engine.state.turns_taken == 0

    engine.take_turn_move(Direction.RIGHT)
    assert engine.state.turns_taken == 1

    engine.take_turn_rest()
    assert engine.state.turns_taken == 2


@given(
    st.lists(
        st.sampled_from(
            [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]
        ),
        min_size=1,
        max_size=20,
    )
)
def test_stamina_stays_within_valid_bounds_for_any_move_sequence(
    directions: list[Direction],
) -> None:
    grid = Grid(width=21, height=21)
    state = GameState(grid=grid, player=Player(position=Position(10, 10)))
    engine = Engine(state)

    for direction in directions:
        engine.take_turn_move(direction)
        assert 0 <= engine.state.player.stamina <= MAX_STAMINA


@given(st.integers(min_value=1, max_value=10))
def test_repeated_single_steps_never_drain_stamina(num_steps: int) -> None:
    grid = Grid(width=30, height=1)
    state = GameState(grid=grid, player=Player(position=Position(15, 0)))
    engine = Engine(state)

    for _ in range(num_steps):
        engine.take_turn_move(Direction.RIGHT)
        assert engine.state.player.stamina == MAX_STAMINA
