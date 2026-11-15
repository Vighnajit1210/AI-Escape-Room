"""Version 2 Streamlit front end. Run with:  streamlit run v2/app.py"""

import logging

import streamlit as st

import game_data as gd
from controller import GameSession, offline_requested

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

st.set_page_config(page_title="AI Escape Room — V2", page_icon="🗝️", layout="wide")


def new_session() -> None:
    ai, mode_note = None, ""
    if offline_requested():
        mode_note = "OFFLINE_MODE=true"
    else:
        try:
            from ai import GeminiAI
            ai = GeminiAI()
        except Exception as exc:  # missing key or SDK problem -> still playable
            mode_note = str(exc)
    st.session_state.game = GameSession(ai)
    st.session_state.mode_note = mode_note
    st.session_state.celebrated = False
    st.session_state.messages = [{"role": "assistant", "text": gd.INTRO, "debug": None}]


if "game" not in st.session_state:
    new_session()

game: GameSession = st.session_state.game
state = game.engine.state


def play(text: str) -> None:
    st.session_state.messages.append({"role": "user", "text": text, "debug": None})
    with st.spinner("The room responds..."):
        out = game.play_turn(text)
    debug = {
        "parsed action": vars(out.action) if out.action else None,
        "intent from": out.intent_source,
        "text from": out.narration_source,
        "engine event": out.event,
        "note": out.note or "-",
    }
    st.session_state.messages.append({"role": "assistant", "text": out.text, "debug": debug})


# ---------------------------------------------------------------- sidebar
with st.sidebar:
    st.header("🧭 Game status")
    if game.online:
        st.success(f"Online — Gemini ({game.ai.model})")
    else:
        st.warning("Offline mode — rule-based parser, no AI narration")
        if st.session_state.mode_note:
            st.caption(f"Reason: {st.session_state.mode_note}")
    st.metric("Puzzles solved", f"{state.puzzles_solved} / 3")
    st.progress(state.puzzles_solved / 3)
    c1, c2 = st.columns(2)
    c1.metric("Moves", state.moves)
    c2.metric("Hints", sum(state.hints_used.values()))
    st.subheader("🎒 Inventory")
    if state.inventory:
        for name in game.engine.inventory_names():
            st.write(f"- {name}")
    else:
        st.caption("Empty")
    st.divider()
    show_debug = st.toggle("Show how V2 handled each turn", value=False)
    if st.button("🔄 Restart game", use_container_width=True):
        new_session()
        st.rerun()

# ---------------------------------------------------------------- main area
st.title("🗝️ AI Escape Room — Version 2")
st.caption(f"{gd.ROOM_NAME} · game engine + Gemini narrator + guardrails")

b1, b2, b3, b4 = st.columns(4)
quick = None
if b1.button("👀 Look around", use_container_width=True):
    quick = "look around"
if b2.button("🎒 Inventory", use_container_width=True):
    quick = "inventory"
if b3.button("💡 Hint", use_container_width=True):
    quick = "hint"
if b4.button("❓ Help", use_container_width=True):
    quick = "help"

typed = st.chat_input("What do you do?", disabled=state.escaped)
if quick or typed:
    play(quick or typed)
    st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["text"])
        if show_debug and msg["debug"]:
            d = msg["debug"]
            act = d["parsed action"] or {}
            act_txt = ", ".join(f"{k}={v}" for k, v in act.items() if v) or "-"
            st.caption(f"🔍 action: `{act_txt}` · intent from **{d['intent from']}** · "
                       f"text from **{d['text from']}** · event `{d['engine event']}` · note: {d['note']}")

if state.escaped:
    if not st.session_state.get("celebrated"):
        st.balloons()
        st.session_state.celebrated = True
    st.success(f"🎉 You escaped in {state.moves} moves using {sum(state.hints_used.values())} hint(s)!")
