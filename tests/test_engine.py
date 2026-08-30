"""Tests für die Spiellogik in wm_dungeon_crawler.engine."""

from hypothesis import given
from hypothesis import strategies as st

from wm_dungeon_crawler.engine import Engine
from wm_dungeon_crawler.levels import create_fixed_level
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


def _fixed_level_engine() -> Engine:
    return Engine(create_fixed_level())


def test_move_blocked_by_wall_has_no_side_effects():
    engine = _fixed_level_engine()
    start = engine.state.player.position

    assert engine.take_turn_move(Direction.RIGHT) is False
    assert engine.state.player.position == start
    assert engine.state.player.stamina == MAX_STAMINA


def test_move_onto_open_floor_succeeds():
    engine = _fixed_level_engine()

    assert engine.take_turn_move(Direction.DOWN) is True
    assert engine.state.player.position == Position(2, 2)


def test_sprint_collects_item_on_intermediate_tile():
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


def test_sprint_blocked_on_second_tile_has_no_side_effects():
    grid = Grid(width=3, height=1, tiles={Position(2, 0): TileType.WALL})
    state = GameState(grid=grid, player=Player(position=Position(0, 0)))
    engine = Engine(state)

    assert engine.take_turn_move(Direction.RIGHT, sprint=True) is False
    assert engine.state.player.position == Position(0, 0)
    assert engine.state.player.stamina == MAX_STAMINA


def test_unlock_fails_without_item_in_inventory():
    grid = Grid(width=3, height=1)
    door = Door(position=Position(1, 0))
    state = GameState(grid=grid, player=Player(position=Position(0, 0)), doors=[door])
    engine = Engine(state)

    assert engine.try_unlock_adjacent_door() is False
    assert door.locked is True


def test_unlock_fails_without_adjacent_door():
    grid = Grid(width=5, height=1)
    door = Door(position=Position(4, 0))
    player = Player(
        position=Position(0, 0),
        inventory=[Item(position=Position(0, 0), name="Schlüssel")],
    )
    state = GameState(grid=grid, player=player, doors=[door])
    engine = Engine(state)

    assert engine.try_unlock_adjacent_door() is False


def test_unlock_succeeds_and_consumes_exactly_one_item():
    grid = Grid(width=3, height=1)
    door = Door(position=Position(1, 0))
    player = Player(
        position=Position(0, 0),
        inventory=[Item(position=Position(0, 0), name="Schlüssel")],
    )
    state = GameState(grid=grid, player=player, doors=[door])
    engine = Engine(state)

    assert engine.try_unlock_adjacent_door() is True
    assert door.locked is False
    assert player.inventory == []


def test_player_walking_into_guard_is_caught():
    grid = Grid(width=3, height=1)
    guard = Guard(patrol_route=[Position(1, 0)])
    state = GameState(grid=grid, player=Player(position=Position(0, 0)), guards=[guard])
    engine = Engine(state)

    engine.take_turn_move(Direction.RIGHT)
    assert engine.state.status is GameStatus.LOST


def test_guard_walking_into_resting_player_is_caught():
    grid = Grid(width=3, height=1)
    guard = Guard(patrol_route=[Position(0, 0), Position(1, 0)])
    state = GameState(grid=grid, player=Player(position=Position(1, 0)), guards=[guard])
    engine = Engine(state)

    engine.take_turn_rest()
    assert engine.state.status is GameStatus.LOST


def test_reaching_exit_wins():
    grid = Grid(width=2, height=1, tiles={Position(1, 0): TileType.EXIT})
    state = GameState(grid=grid, player=Player(position=Position(0, 0)))
    engine = Engine(state)

    assert engine.take_turn_move(Direction.RIGHT) is True
    assert engine.state.status is GameStatus.WON


def test_winning_takes_priority_over_being_caught_on_the_same_move():
    grid = Grid(width=2, height=1, tiles={Position(1, 0): TileType.EXIT})
    guard = Guard(patrol_route=[Position(1, 0)])
    state = GameState(grid=grid, player=Player(position=Position(0, 0)), guards=[guard])
    engine = Engine(state)

    engine.take_turn_move(Direction.RIGHT)
    assert engine.state.status is GameStatus.WON


def test_no_action_possible_after_losing():
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

    assert engine.take_turn_move(Direction.LEFT) is False
    assert engine.state.player.position == Position(2, 0)

    engine.take_turn_rest()
    assert engine.state.player.stamina == 0

    assert engine.try_unlock_adjacent_door() is False


@given(
    st.lists(
        st.sampled_from(
            [Direction.UP, Direction.DOWN, Direction.LEFT, Direction.RIGHT]
        ),
        min_size=1,
        max_size=20,
    )
)
def test_stamina_stays_within_valid_bounds_for_any_move_sequence(directions):
    grid = Grid(width=21, height=21)
    state = GameState(grid=grid, player=Player(position=Position(10, 10)))
    engine = Engine(state)

    for direction in directions:
        engine.take_turn_move(direction)
        assert 0 <= engine.state.player.stamina <= MAX_STAMINA


@given(st.integers(min_value=1, max_value=10))
def test_repeated_single_steps_never_drain_stamina(num_steps):
    grid = Grid(width=30, height=1)
    state = GameState(grid=grid, player=Player(position=Position(15, 0)))
    engine = Engine(state)

    for _ in range(num_steps):
        engine.take_turn_move(Direction.RIGHT)
        assert engine.state.player.stamina == MAX_STAMINA
