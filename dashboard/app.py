import streamlit as st

from dashboard.utils.db import get_last_successful_refresh

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

last_refresh = get_last_successful_refresh()
if last_refresh:
    display_date = f"{last_refresh:%b} {last_refresh.day}, {last_refresh.year}"
    st.sidebar.markdown(
        '<div style="margin-top:1.5rem; padding-top:0.6rem; '
        'border-top:1px solid rgba(255,255,255,0.07); '
        'color:rgba(255,255,255,0.43); font-size:11px;">'
        f'Data updated {display_date}</div>',
        unsafe_allow_html=True,
    )
