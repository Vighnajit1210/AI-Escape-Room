"""
Rule-based command parser.

Used in two situations:
  1. Offline mode (no API key), so the game is always playable.
  2. As a fallback when Gemini fails, times out or returns invalid JSON.
"""

from __future__ import annotations

import re

import game_data as gd
from engine import Action, normalise


def _find(text: str, table: dict) -> str | None:
    """Return the id whose alias appears in text. Longer aliases win ('brass key' over 'key')."""
    best, best_len = None, 0
    for key, entry in table.items():
        for alias in entry["aliases"]:
            if re.search(rf"\b{re.escape(alias)}\b", text) and len(alias) > best_len:
                best, best_len = key, len(alias)
    return best


def find_object(text: str) -> str | None:
    return _find(text, gd.OBJECTS)


def find_item(text: str) -> str | None:
    return _find(text, gd.ITEMS)


def parse_command(raw: str) -> Action:
    text = normalise(raw)
    if not text:
        return Action("unknown")
    words = text.split()
    first = words[0]

    if text in ("help", "commands", "what can i do") or first == "help":
        return Action("help")
    if first in ("hint", "clue") or "give me a hint" in text or "i m stuck" in text or "im stuck" in text:
        return Action("hint")
    if first in ("inventory", "inv") or text == "i" or "what do i have" in text or "my items" in text:
        return Action("inventory")
    if text in ("look", "look around", "l") or text.startswith("look around") or text == "where am i":
        return Action("look")

    # Codes and answers: "enter 1234 on safe", "type 1234", "answer bottle", "the answer is bottle"
    code = re.search(r"\b(\d{1,8})\b", text)
    if text.isdigit():
        return Action("solve", target="safe", value=text)
    if first in ("enter", "type", "input", "dial", "punch") and code:
        return Action("solve", target="safe", value=code.group(1))
    m = re.match(r"(?:answer|solve|say|guess|spell)\s+(?:is\s+)?(.+)", text) or re.search(r"the answer is\s+(.+)", text)
    if m:
        value = m.group(1)
        value = re.sub(r"\s+(on|to|for|at)\s+the\s+\w+$|\s+(on|to|for|at)\s+\w+$", "", value).strip()
        target = "safe" if value.isdigit() else "bookshelf"
        return Action("solve", target=target, value=value)

    obj = find_object(text)
    item = find_item(text)
    # "key" is both an alias of brass key and part of "keypad"/"keycard": _find uses word boundaries,
    # and "keypad" is an object alias, so "enter code on keypad" is not mistaken for the key.

    if first in ("use", "try", "put", "insert", "swipe", "unlock", "open") and item:
        if first == "unlock" and obj is None:
            obj = "desk" if item == "brass_key" else None
        return Action("use", target=obj, item=item)
    if first in ("take", "grab", "pick", "get"):
        return Action("take", target=obj if not item else None, item=item)
    if first in ("examine", "inspect", "check", "look", "read", "search", "study", "x", "open"):
        if item and (first == "read" or obj is None):
            return Action("examine", item=item)
        return Action("examine", target=obj)
    if obj and not item:
        return Action("examine", target=obj)
    return Action("unknown")
