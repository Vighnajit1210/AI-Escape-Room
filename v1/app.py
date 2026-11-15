"""Version 1 Streamlit front end. Run with:  streamlit run v1/app.py"""

import streamlit as st

from game_master import ESCAPE_TOKEN, INTRO, ask_game_master, get_client, has_escaped

st.set_page_config(page_title="AI Escape Room — V1", page_icon="🗝️")
st.title("🗝️ AI Escape Room — Version 1")
st.caption("Gemini runs the entire game from a single prompt.")

if "history" not in st.session_state:
    st.session_state.history = [{"role": "model", "text": INTRO}]
    st.session_state.escaped = False

if st.sidebar.button("Restart game"):
    st.session_state.clear()
    st.rerun()

for msg in st.session_state.history:
    with st.chat_message("assistant" if msg["role"] == "model" else "user"):
        st.markdown(msg["text"].replace(ESCAPE_TOKEN, ""))

if st.session_state.escaped:
    st.success("🎉 You escaped!")

if prompt := st.chat_input("What do you do?"):
    with st.chat_message("user"):
        st.markdown(prompt)
    client = get_client()  # V1: crashes with a red error if the key is missing
    reply = ask_game_master(client, st.session_state.history, prompt)
    st.session_state.history.append({"role": "user", "text": prompt})
    st.session_state.history.append({"role": "model", "text": reply})
    if has_escaped(reply):
        st.session_state.escaped = True
    st.rerun()
