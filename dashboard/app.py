import streamlit as st

st.set_page_config(
    page_title="NHL Shot Analytics",
    page_icon="🏒",
    layout="wide",
)

pg = st.navigation([
    st.Page("pages/teams.py", title="Teams", url_path="teams"),
    st.Page("pages/player_card.py", title="Players", url_path="player_card")
])
pg.run()
