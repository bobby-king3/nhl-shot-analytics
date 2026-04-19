import streamlit as st

def detect_change(session_key, new_value):
    prev_value = st.session_state.get(session_key)
    if new_value != prev_value:
        st.session_state[session_key] = new_value
        return True
    return False