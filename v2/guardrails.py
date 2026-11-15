"""
Input and output guardrails for Version 2.

Input guard:  rejects empty / overly long messages and obvious prompt-injection
              attempts BEFORE anything is sent to Gemini.
Output guard: checks Gemini's narration before it is shown. If the narration
              mentions a secret the player has not earned, invents a new code,
              or drops an important fact, the engine's plain text is shown instead.

The input guard is a heuristic and can be bypassed by creative wording. That is
acceptable because it is only the first layer: Gemini never sees the solutions,
and the engine — not Gemini — decides whether an answer is correct.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

import game_data as gd

INJECTION_PATTERNS = [
    r"ignore (all |any |the |your )?(previous |prior |above )?(instructions|rules|prompt)",
    r"disregard (all |the |your )?(previous |prior )?(instructions|rules)",
    r"system prompt",
    r"you are now",
    r"act as (an? )?(admin|developer|game ?master|dan)",
    r"developer mode",
    r"(reveal|tell me|show me|give me|what is|what s|whats) (the |all )?(solution|solutions|answer|answers|code|password|combination)s?\b",
    r"\bjailbreak\b",
    r"pretend (that )?(you|i) (are|am|have)",
    r"print \[?escaped\]?",
    r"\[escaped\]",
]

GUARDRAIL_REPLY = (
    "The room's old magic ignores your attempt to bend its rules. "
    "The only way out is to solve the puzzles. Type 'hint' if you are stuck."
)


@dataclass
class GuardResult:
    allowed: bool
    reason: str = ""
    message: str = ""
    cleaned: str = ""


def clean_input(text: str) -> str:
    """Normalise unicode and remove control characters."""
    text = unicodedata.normalize("NFKC", text)
    text = "".join(ch for ch in text if ch.isprintable())
    return text.strip()


def check_input(raw: str) -> GuardResult:
    text = clean_input(raw)
    if not text:
        return GuardResult(False, "empty", "Say something — what do you want to do?")
    if len(text) > gd.MAX_INPUT_LENGTH:
        return GuardResult(False, "too_long",
                           f"That is too long. Please keep commands under {gd.MAX_INPUT_LENGTH} characters.")
    lowered = re.sub(r"[^a-z0-9\[\] ]", " ", text.lower())
    lowered = re.sub(r"\s+", " ", lowered)
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, lowered):
            return GuardResult(False, "injection", GUARDRAIL_REPLY)
    return GuardResult(True, cleaned=text)


def check_narration(narration: str, facts: str, must_mention: list[str], revealed: str) -> tuple[bool, str]:
    """Return (ok, reason). 'facts' is the engine text the narration was based on."""
    if not narration or not narration.strip():
        return False, "empty"
    if len(narration) > 1200:
        return False, "too_long"
    low = narration.lower()
    allowed = (facts + " " + revealed).lower()

    # 1. Secret answers must not appear unless they are already part of the facts/revealed text.
    for secrets in gd.SOLUTIONS.values():
        for secret in secrets:
            if re.search(rf"\b{re.escape(secret)}\b", low) and secret not in allowed:
                return False, f"leaked_secret:{secret}"

    # 2. No invented numbers (a made-up code would mislead the player).
    for number in re.findall(r"\d{2,}", narration):
        if number not in allowed:
            return False, f"invented_number:{number}"

    # 3. Important facts must survive the rewrite.
    for term in must_mention:
        if term.lower() not in low:
            return False, f"missing:{term}"

    # 4. The narration must not claim an escape the engine did not confirm.
    if "escaped" not in facts.lower() and re.search(r"\byou (have )?escaped\b|\byou are free\b", low):
        return False, "false_escape"
    return True, "ok"
