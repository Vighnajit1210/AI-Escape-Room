"""
Static content of the escape room: objects, items, puzzle answers and hints.

In Version 2 this data lives ONLY in Python. The solutions are never placed in a
prompt, so Gemini cannot leak them even if a player tricks it.
"""

ROOM_NAME = "The Clockmaker's Study"

INTRO = (
    "You wake up in a dusty Victorian study. The door behind you is locked and a small "
    "red light blinks on its card reader. Around you are a tall bookshelf, an old writing "
    "desk, a silent grandfather clock, an oil painting of a ship and an iron safe. "
    "Type what you want to do, or type 'help'."
)

# Objects in the room. Aliases are the words a player may use for them.
OBJECTS = {
    "bookshelf": {"name": "bookshelf", "aliases": ["bookshelf", "bookcase", "shelf", "shelves", "books", "riddle", "carving"]},
    "desk": {"name": "writing desk", "aliases": ["desk", "drawer", "writing desk"]},
    "clock": {"name": "grandfather clock", "aliases": ["clock", "grandfather clock", "plaque", "pendulum"]},
    "painting": {"name": "oil painting", "aliases": ["painting", "picture", "ship", "art", "canvas"]},
    "safe": {"name": "iron safe", "aliases": ["safe", "keypad", "iron safe"]},
    "door": {"name": "door", "aliases": ["door", "card reader", "reader", "exit", "lock"]},
}

# Items the player can carry.
ITEMS = {
    "brass_key": {"name": "brass key", "aliases": ["brass key", "key"]},
    "diary_page": {"name": "torn diary page", "aliases": ["diary page", "diary", "page", "torn page"]},
    "keycard": {"name": "exit keycard", "aliases": ["exit keycard", "keycard", "key card", "card"]},
}

# Puzzle solutions. Checked in code only.
SOLUTIONS = {
    "bookshelf": {"bottle", "a bottle", "bottles"},
    "safe": {"1887"},
}

RIDDLE = "I have a neck but no head, and I wear a cap. What am I?"
DIARY_TEXT = "The safe remembers the year the clock stopped."
PLAQUE_TEXT = "Stopped forever in 1887."

MAX_SAFE_ATTEMPTS = 5      # wrong codes before the keypad jams
SAFE_LOCKOUT_MOVES = 3     # how many moves the keypad stays jammed
MAX_INPUT_LENGTH = 300

# Hints are tiered: each request reveals a little more. Keys are puzzle stages.
HINTS = {
    "riddle": [
        "The carving on the bookshelf is a riddle. Try examining the bookshelf.",
        "Think of something you might find on a shelf in a kitchen or a bar.",
        "It holds liquid and you take its cap off to pour. Answer with: answer <word>.",
    ],
    "drawer": [
        "You found something in the bookshelf. Is there anything in the room with a keyhole?",
        "The writing desk has a locked drawer.",
        "Try: use brass key on desk.",
    ],
    "safe": [
        "Read the diary page you found in the drawer.",
        "The grandfather clock has a plaque. Examine it.",
        "Enter the year from the plaque on the safe, for example: enter <code> on safe.",
    ],
    "door": [
        "The safe gave you something. How do you open an electronic lock?",
        "Try: use keycard on door.",
        "Type exactly: use keycard on door.",
    ],
}
