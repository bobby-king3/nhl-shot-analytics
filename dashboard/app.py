import streamlit as st

st.set_page_config(
    page_title="NHL Shot Analytics",
    page_icon="🏒",
    layout="wide",
)

pg = st.navigation([
    st.Page("pages/player_card.py",  title="Player Card"),
])
pg.run()
