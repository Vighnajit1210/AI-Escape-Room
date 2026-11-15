"""
Turn pipeline for Version 2:

  player text
     -> input guardrail            (block injections / bad input, no API call)
     -> intent: rule parser first  (cheap, deterministic)
               -> Gemini JSON      (only if rules don't understand; validated)
     -> game engine                (single source of truth, checks answers)
     -> narration: Gemini rewrite  (online mode only)
     -> output guardrail           (no leaks, no invented numbers, facts kept)
     -> fallback to engine text if anything fails
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass

import guardrails
from command_parser import parse_command
from engine import Action, GameEngine

log = logging.getLogger("escape_room.controller")


@dataclass
class TurnOutput:
    text: str
    escaped: bool = False
    action: Action | None = None
    intent_source: str = ""     # "rules" | "gemini" | "guardrail" | "fallback"
    narration_source: str = ""  # "gemini" | "engine" | "guardrail"
    note: str = ""              # why a fallback happened (shown in the debug panel)
    event: str = ""


def offline_requested() -> bool:
    return os.getenv("OFFLINE_MODE", "false").strip().lower() in ("1", "true", "yes")


class GameSession:
    def __init__(self, ai=None):
        """ai: a GeminiAI instance, or None for offline mode."""
        self.engine = GameEngine()
        self.ai = ai

    @property
    def online(self) -> bool:
        return self.ai is not None

    def play_turn(self, raw_text: str) -> TurnOutput:
        guard = guardrails.check_input(raw_text)
        if not guard.allowed:
            log.info("Input blocked: %s", guard.reason)
            return TurnOutput(guard.message, intent_source="guardrail", narration_source="guardrail",
                              note=f"input blocked ({guard.reason})", event=f"blocked_{guard.reason}")
        text = guard.cleaned
        notes = []

        # 1. Understand the player.
        action = parse_command(text)
        intent_source = "rules"
        if action.verb == "unknown" and self.online:
            try:
                action = self.ai.interpret(text)
                intent_source = "gemini"
            except Exception as exc:
                notes.append(f"Gemini intent failed: {exc}")
                intent_source = "fallback"

        # 2. Let the engine decide what happens.
        result = self.engine.apply(action)

        # 3. Describe it.
        output_text, narration_source = result.text, "engine"
        if self.online and result.event not in ("help", "unknown"):
            try:
                narration = self.ai.narrate(text, result.text)
                ok, reason = guardrails.check_narration(
                    narration, result.text, result.must_mention, self.engine.revealed_text())
                if ok:
                    output_text, narration_source = narration, "gemini"
                else:
                    notes.append(f"narration rejected ({reason})")
            except Exception as exc:
                notes.append(f"Gemini narration failed: {exc}")

        log.info("turn=%d action=%s event=%s intent=%s narration=%s",
                 self.engine.state.moves, action, result.event, intent_source, narration_source)
        return TurnOutput(output_text, result.escaped, action, intent_source, narration_source,
                          "; ".join(notes), result.event)
