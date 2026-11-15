"""
Deterministic game engine for Version 2.

The engine is the single source of truth: it owns the inventory, the puzzle state
and the win condition, and it checks every answer in plain Python. The LLM never
decides whether something succeeded — it only receives the engine's result and
describes it.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import game_data as gd

VERBS = ["look", "examine", "take", "use", "solve", "inventory", "hint", "help", "unknown"]


@dataclass
class Action:
    verb: str
    target: str | None = None   # object id from game_data.OBJECTS
    item: str | None = None     # item id from game_data.ITEMS
    value: str | None = None    # free text, e.g. a riddle answer or a code


@dataclass
class TurnResult:
    text: str                                   # factual, plain description of what happened
    success: bool = True
    must_mention: list[str] = field(default_factory=list)  # words the narration must keep
    escaped: bool = False
    event: str = ""                             # short machine-readable label, used in tests/logs


@dataclass
class GameState:
    inventory: list[str] = field(default_factory=list)
    flags: set[str] = field(default_factory=set)
    moves: int = 0
    hints_used: dict[str, int] = field(default_factory=dict)
    safe_wrong_attempts: int = 0
    safe_locked_until: int = 0
    escaped: bool = False

    @property
    def puzzles_solved(self) -> int:
        return sum(f in self.flags for f in ("riddle_solved", "drawer_open", "safe_open"))

    def stage(self) -> str:
        if "riddle_solved" not in self.flags:
            return "riddle"
        if "drawer_open" not in self.flags:
            return "drawer"
        if "safe_open" not in self.flags:
            return "safe"
        return "door"


def normalise(text: str) -> str:
    """Lower-case, strip punctuation and extra spaces so 'A Bottle!' == 'a bottle'."""
    text = re.sub(r"[^a-z0-9 ]", " ", text.lower())
    return re.sub(r"\s+", " ", text).strip()


class GameEngine:
    def __init__(self) -> None:
        self.state = GameState()

    # ------------------------------------------------------------------ helpers
    def _has(self, item: str) -> bool:
        return item in self.state.inventory

    def _give(self, item: str) -> None:
        if item not in self.state.inventory:
            self.state.inventory.append(item)

    def inventory_names(self) -> list[str]:
        return [gd.ITEMS[i]["name"] for i in self.state.inventory]

    def revealed_text(self) -> str:
        """Everything the player has legitimately seen; used by the output guard."""
        parts = [gd.INTRO]
        if "clock_examined" in self.state.flags:
            parts.append(gd.PLAQUE_TEXT)
        if "riddle_solved" in self.state.flags:
            parts.append("bottle")
        return " ".join(parts)

    # ------------------------------------------------------------------ main entry
    def apply(self, action: Action) -> TurnResult:
        if self.state.escaped:
            return TurnResult("You have already escaped! Press 'Restart game' to play again.", event="already_escaped")

        self.state.moves += 1
        handler = getattr(self, f"_do_{action.verb}", None)
        if handler is None:
            return self._do_unknown(action)
        return handler(action)

    # ------------------------------------------------------------------ verbs
    def _do_help(self, a: Action) -> TurnResult:
        return TurnResult(
            "Commands you can use: look, examine <thing>, take <item>, use <item> on <thing>, "
            "answer <word>, enter <code> on safe, inventory, hint. You can also just write naturally.",
            event="help",
        )

    def _do_look(self, a: Action) -> TurnResult:
        details = [
            "You are in a dusty Victorian study.",
            "There is a tall bookshelf" + (" with an open hidden compartment" if "riddle_solved" in self.state.flags else " with something carved into it") + ".",
            "There is an old writing desk" + (" with its drawer open" if "drawer_open" in self.state.flags else " with a locked drawer") + ".",
            "A silent grandfather clock stands in the corner.",
            "An oil painting of a ship hangs on the wall.",
            "An iron safe with a keypad sits on the floor" + (" with its door open" if "safe_open" in self.state.flags else "") + ".",
            "The exit door is locked by a card reader with a blinking red light.",
        ]
        return TurnResult(" ".join(details), event="look")

    def _do_inventory(self, a: Action) -> TurnResult:
        if not self.state.inventory:
            return TurnResult("You are not carrying anything.", event="inventory")
        names = self.inventory_names()
        return TurnResult("You are carrying: " + ", ".join(names) + ".", must_mention=names, event="inventory")

    def _do_examine(self, a: Action) -> TurnResult:
        # Items in the inventory can be examined too.
        if a.item:
            if not self._has(a.item):
                return TurnResult("You don't have that.", success=False, event="examine_missing_item")
            if a.item == "diary_page":
                return TurnResult(f'The torn diary page reads: "{gd.DIARY_TEXT}"', must_mention=["safe", "clock"], event="read_diary")
            return TurnResult(f"It is a {gd.ITEMS[a.item]['name']}. It might be useful somewhere.", event="examine_item")

        t = a.target
        if t is None:
            return TurnResult("What do you want to examine? Try the bookshelf, desk, clock, painting, safe or door.", success=False, event="examine_nothing")
        if t == "bookshelf":
            if "riddle_solved" in self.state.flags:
                return TurnResult("The hidden compartment in the bookshelf is open and empty now.", event="examine_bookshelf_done")
            return TurnResult(f'Words are carved into the wood of the bookshelf: "{gd.RIDDLE}" Below them is a small dial with letters.',
                              must_mention=["neck", "cap"], event="examine_bookshelf")
        if t == "desk":
            if "drawer_open" in self.state.flags:
                return TurnResult("The desk drawer is open and empty.", event="examine_desk_done")
            return TurnResult("The writing desk has a single drawer with a small brass keyhole. It is locked.", must_mention=["keyhole"], event="examine_desk")
        if t == "clock":
            self.state.flags.add("clock_examined")
            return TurnResult(f'The grandfather clock\'s hands are frozen. A brass plaque reads: "{gd.PLAQUE_TEXT}"',
                              must_mention=["1887"], event="examine_clock")
        if t == "painting":
            return TurnResult('The painting shows a ship in a storm. Scratched into the frame are the words: "Time tells the truth."',
                              must_mention=["Time tells the truth"], event="examine_painting")
        if t == "safe":
            if "safe_open" in self.state.flags:
                return TurnResult("The safe is open and empty.", event="examine_safe_done")
            return TurnResult("A heavy iron safe with a 4-digit keypad.", must_mention=["4-digit"], event="examine_safe")
        if t == "door":
            return TurnResult("The exit door is solid oak. A card reader next to it blinks red.", must_mention=["card reader"], event="examine_door")
        return TurnResult("You don't see anything special.", success=False, event="examine_other")

    def _do_take(self, a: Action) -> TurnResult:
        if a.item and self._has(a.item):
            return TurnResult(f"You already have the {gd.ITEMS[a.item]['name']}.", event="take_already")
        if a.target:
            return TurnResult(f"The {gd.OBJECTS[a.target]['name']} is far too heavy to carry.", success=False, event="take_object")
        return TurnResult("You don't see that here. Items appear when you solve the puzzles.", success=False, event="take_missing")

    def _do_use(self, a: Action) -> TurnResult:
        if not a.item:
            return TurnResult("What do you want to use? Check your inventory.", success=False, event="use_no_item")
        if not self._has(a.item):
            # The player cannot simply claim to own something.
            return TurnResult(f"You don't have the {gd.ITEMS[a.item]['name']}.", success=False, event="use_missing_item")
        if a.item == "brass_key" and a.target == "desk":
            if "drawer_open" in self.state.flags:
                return TurnResult("The drawer is already open.", event="drawer_already_open")
            self.state.flags.add("drawer_open")
            self._give("diary_page")
            return TurnResult(
                f'The brass key turns with a click and the drawer slides open. Inside is a torn diary page. It reads: "{gd.DIARY_TEXT}" You take the page.',
                must_mention=["diary page"], event="drawer_opened")
        if a.item == "keycard" and a.target == "door":
            self.state.escaped = True
            self.state.flags.add("escaped")
            return TurnResult("You swipe the exit keycard. The light turns green and the door swings open. You have escaped!",
                              must_mention=["escaped"], escaped=True, event="escaped")
        if a.item == "diary_page":
            return self._do_examine(Action("examine", item="diary_page"))
        target_name = gd.OBJECTS[a.target]["name"] if a.target else "anything"
        return TurnResult(f"You try the {gd.ITEMS[a.item]['name']} on the {target_name}, but nothing happens.", success=False, event="use_nothing")

    def _do_solve(self, a: Action) -> TurnResult:
        if not a.value:
            return TurnResult("What is your answer? For example: answer <word> or enter <code> on safe.", success=False, event="solve_empty")
        answer = normalise(a.value)
        target = a.target
        if target not in ("bookshelf", "safe"):
            # Infer the lock from the answer: digits go to the safe, words to the riddle.
            target = "safe" if answer.isdigit() else "bookshelf"

        if target == "bookshelf":
            if "riddle_solved" in self.state.flags:
                return TurnResult("You already solved the riddle.", event="riddle_already")
            if answer in gd.SOLUTIONS["bookshelf"]:
                self.state.flags.add("riddle_solved")
                self._give("brass_key")
                return TurnResult("You turn the letter dial to spell your answer. With a click, a hidden compartment in the bookshelf opens. Inside is a brass key. You take it.",
                                  must_mention=["brass key"], event="riddle_solved")
            return TurnResult("You spell out your answer on the dial, but nothing happens. That is not the answer.", success=False, event="riddle_wrong")

        # target == safe
        if "safe_open" in self.state.flags:
            return TurnResult("The safe is already open.", event="safe_already")
        if self.state.moves <= self.state.safe_locked_until:
            left = self.state.safe_locked_until - self.state.moves + 1
            return TurnResult(f"The keypad is jammed after too many wrong codes. Try again in {left} move(s).", success=False, event="safe_locked")
        if not (answer.isdigit() and len(answer) == 4):
            return TurnResult("The keypad only accepts 4-digit codes.", success=False, event="safe_invalid")
        if answer in gd.SOLUTIONS["safe"]:
            self.state.flags.add("safe_open")
            self._give("keycard")
            return TurnResult("The keypad beeps and the safe door swings open. Inside is an exit keycard. You take it.",
                              must_mention=["keycard"], event="safe_opened")
        self.state.safe_wrong_attempts += 1
        if self.state.safe_wrong_attempts % gd.MAX_SAFE_ATTEMPTS == 0:
            self.state.safe_locked_until = self.state.moves + gd.SAFE_LOCKOUT_MOVES
            return TurnResult(f"Wrong code. The keypad buzzes angrily and jams for {gd.SAFE_LOCKOUT_MOVES} moves.", success=False, event="safe_jammed")
        left = gd.MAX_SAFE_ATTEMPTS - (self.state.safe_wrong_attempts % gd.MAX_SAFE_ATTEMPTS)
        return TurnResult(f"The keypad flashes red. Wrong code. {left} attempt(s) before it jams.", success=False, event="safe_wrong")

    def _do_hint(self, a: Action) -> TurnResult:
        stage = self.state.stage()
        used = self.state.hints_used.get(stage, 0)
        hints = gd.HINTS[stage]
        hint = hints[min(used, len(hints) - 1)]
        self.state.hints_used[stage] = used + 1
        return TurnResult(f"Hint: {hint}", event=f"hint_{stage}")

    def _do_unknown(self, a: Action) -> TurnResult:
        self.state.moves -= 1  # don't punish the player for being misunderstood
        return TurnResult("Nothing happens. Try examining things in the room, or type 'help' or 'hint'.", success=False, event="unknown")
