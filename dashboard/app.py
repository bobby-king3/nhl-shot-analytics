from dotenv import load_dotenv
load_dotenv()

import streamlit as st

st.set_page_config(
    page_title="NHL Shot Intelligence",
    page_icon="🏒",
    layout="wide",
)

pg = st.navigation([
    st.Page("pages/league_pulse.py", title="League Pulse"),
    st.Page("pages/player_card.py",  title="Player Card"),
])
pg.run()
