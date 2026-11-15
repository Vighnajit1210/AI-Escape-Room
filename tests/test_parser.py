"""Tests for the rule-based command parser."""

import pytest

from command_parser import parse_command


@pytest.mark.parametrize("text, verb, target, item, value", [
    ("look around", "look", None, None, None),
    ("examine the bookshelf", "examine", "bookshelf", None, None),
    ("inspect clock", "examine", "clock", None, None),
    ("check the card reader", "examine", "door", None, None),
    ("use key on desk", "use", "desk", "brass_key", None),
    ("use the brass key on the drawer", "use", "desk", "brass_key", None),
    ("swipe keycard on door", "use", "door", "keycard", None),
    ("enter 1887 on safe", "solve", "safe", None, "1887"),
    ("1887", "solve", "safe", None, "1887"),
    ("answer bottle", "solve", "bookshelf", None, "bottle"),
    ("the answer is a bottle", "solve", "bookshelf", None, "a bottle"),
    ("read diary page", "examine", None, "diary_page", None),
    ("inventory", "inventory", None, None, None),
    ("hint", "hint", None, None, None),
    ("dance wildly", "unknown", None, None, None),
])
def test_parse(text, verb, target, item, value):
    a = parse_command(text)
    assert (a.verb, a.target, a.item, a.value) == (verb, target, item, value)


def test_keypad_is_not_confused_with_key():
    a = parse_command("examine keypad")
    assert a.target == "safe" and a.item is None
