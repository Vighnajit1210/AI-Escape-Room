"""Unit tests for the deterministic game engine."""

from engine import Action, GameEngine


def solve_to_safe(engine):
    engine.apply(Action("solve", "bookshelf", value="bottle"))
    engine.apply(Action("use", "desk", "brass_key"))


def test_full_playthrough_escapes():
    e = GameEngine()
    solve_to_safe(e)
    assert e.apply(Action("solve", "safe", value="1887")).event == "safe_opened"
    r = e.apply(Action("use", "door", "keycard"))
    assert r.escaped and e.state.escaped
    assert e.state.puzzles_solved == 3


def test_riddle_answer_is_normalised():
    e = GameEngine()
    assert e.apply(Action("solve", "bookshelf", value="  A BOTTLE! ")).event == "riddle_solved"
    assert "brass_key" in e.state.inventory


def test_wrong_riddle_answer_gives_nothing():
    e = GameEngine()
    assert e.apply(Action("solve", "bookshelf", value="giraffe")).event == "riddle_wrong"
    assert e.state.inventory == []


def test_cannot_use_item_player_does_not_have():
    e = GameEngine()
    r = e.apply(Action("use", "door", "keycard"))
    assert r.event == "use_missing_item" and not e.state.escaped


def test_off_by_one_code_rejected():
    e = GameEngine()
    solve_to_safe(e)
    assert e.apply(Action("solve", "safe", value="1888")).event == "safe_wrong"
    assert "keycard" not in e.state.inventory


def test_safe_only_accepts_four_digits():
    e = GameEngine()
    assert e.apply(Action("solve", "safe", value="18870")).event == "safe_invalid"


def test_brute_force_jams_keypad():
    e = GameEngine()
    events = [e.apply(Action("solve", "safe", value=f"{1000 + i}")).event for i in range(5)]
    assert events[-1] == "safe_jammed"
    # Even the correct code is refused while jammed.
    assert e.apply(Action("solve", "safe", value="1887")).event == "safe_locked"


def test_answer_target_is_inferred():
    e = GameEngine()
    assert e.apply(Action("solve", value="bottle")).event == "riddle_solved"
    assert e.apply(Action("solve", value="1887")).event == "safe_opened"


def test_hints_are_tiered_and_follow_progress():
    e = GameEngine()
    first = e.apply(Action("hint")).text
    second = e.apply(Action("hint")).text
    assert first != second
    e.apply(Action("solve", "bookshelf", value="bottle"))
    assert e.apply(Action("hint")).event == "hint_drawer"


def test_unknown_action_does_not_cost_a_move():
    e = GameEngine()
    e.apply(Action("unknown"))
    assert e.state.moves == 0
