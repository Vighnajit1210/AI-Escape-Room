"""
Version 1 — "the LLM is the whole game".

The entire escape room (story, objects, puzzles AND their solutions) is written
into one system prompt. Every player message is appended to the chat history and
sent to Gemini, which decides what happens, whether an answer is correct and
whether the player has escaped.

This is the simplest possible design. It works for a quick demo, but it has
serious weaknesses that are documented in docs/version1.md and fixed in v2/.
"""

import os

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# The token Gemini must print when the player escapes. The app looks for it.
ESCAPE_TOKEN = "[ESCAPED]"

SYSTEM_PROMPT = f"""
You are the game master of a text-based escape room called "The Clockmaker's Study".
Describe scenes vividly in 2-4 sentences. Stay in character.

ROOM: A dusty Victorian study. The door is locked by an electronic card reader.
Objects: a tall bookshelf, an old writing desk with a locked drawer, a stopped
grandfather clock with a brass plaque, an oil painting of a ship, and an iron safe
with a 4-digit keypad.

PUZZLES (in order):
1. The bookshelf has a riddle carved into it: "I have a neck but no head, and I
   wear a cap." Answer: BOTTLE. When the player answers BOTTLE, a hidden
   compartment opens and they get a BRASS KEY.
2. The BRASS KEY opens the desk drawer. Inside is a torn diary page saying:
   "The safe remembers the year the clock stopped."
3. The clock's plaque says "Stopped forever in 1887". The safe code is 1887.
   The safe contains an EXIT KEYCARD.
4. Using the EXIT KEYCARD on the door lets the player escape.

RULES:
- Never reveal the answers directly. Give small hints if the player is stuck.
- Keep track of the player's inventory.
- When the player escapes, congratulate them and write {ESCAPE_TOKEN} at the end.
"""

INTRO = (
    "You wake up in a dusty Victorian study. The door behind you is locked and a "
    "small red light blinks on its card reader. A grandfather clock stands silent "
    "in the corner. Type what you want to do."
)


def get_client() -> genai.Client:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set. Copy .env.example to .env and add your key.")
    return genai.Client(api_key=api_key)


def ask_game_master(client: genai.Client, history: list[dict], player_input: str) -> str:
    """Send the whole conversation plus the new message to Gemini and return its reply.

    history is a list of {"role": "user" | "model", "text": str}.
    """
    contents = [
        types.Content(role=m["role"], parts=[types.Part(text=m["text"])]) for m in history
    ]
    contents.append(types.Content(role="user", parts=[types.Part(text=player_input)]))

    response = client.models.generate_content(
        model=MODEL,
        contents=contents,
        config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT, temperature=0.9),
    )
    return response.text or ""


def has_escaped(reply: str) -> bool:
    return ESCAPE_TOKEN in reply
