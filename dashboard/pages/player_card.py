import streamlit as st
import plotly.graph_objects as go
import numpy as np
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from dashboard.components.rink import make_rink_figure
from dashboard.utils.db import (
    get_player_stats, get_player_shots, get_all_players, get_available_seasons, get_teams
)
from dashboard.utils.video import get_mp4_url

TEAM_COLORS = {
    "ANA": ("#FC4C02", "#B09862"), "BOS": ("#FFB81C", "#000000"),
    "BUF": ("#002654", "#FCB514"), "CAR": ("#CC0000", "#000000"),
    "CBJ": ("#002654", "#CE1126"), "CGY": ("#C8102E", "#F1BE48"),
    "CHI": ("#CF0A2C", "#000000"), "COL": ("#6F263D", "#236192"),
    "DAL": ("#006847", "#8F8F8C"), "DET": ("#CE1126", "#FFFFFF"),
    "EDM": ("#FF4C00", "#041E42"), "FLA": ("#041E42", "#C8102E"),
    "LAK": ("#111111", "#A2AAAD"), "MIN": ("#154734", "#A6192E"),
    "MTL": ("#AF1E2D", "#192168"), "NJD": ("#CE1126", "#000000"),
    "NSH": ("#FFB81C", "#041E42"), "NYI": ("#00539B", "#F47D30"),
    "NYR": ("#0038A8", "#CE1126"), "OTT": ("#C8102E", "#C69214"),
    "PHI": ("#F74902", "#000000"), "PIT": ("#FCB514", "#000000"),
    "SEA": ("#001628", "#99D9D9"), "SJS": ("#006D75", "#EA7200"),
    "STL": ("#002F87", "#FCB514"), "TBL": ("#002868", "#FFFFFF"),
    "TOR": ("#003E7E", "#FFFFFF"), "UTA": ("#69B3E7", "#010101"),
    "VAN": ("#00843D", "#00205B"), "VGK": ("#B4975A", "#333F42"),
    "WSH": ("#041E42", "#C8102E"), "WPG": ("#041E42", "#004C97"),
}
DEFAULT_COLORS = ("#C8102E", "#1A1A2E")


def team_colors(abbrev):
    return TEAM_COLORS.get(abbrev, DEFAULT_COLORS)


st.markdown("""
<style>
  .block-container {
    padding-top: 1rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    max-width: 100% !important;
  }
  .stat-card {
    background: linear-gradient(135deg, var(--team-primary-faint, rgba(200,16,46,0.08)) 0%, rgba(255,255,255,0.03) 100%);
    border: 1px solid rgba(255,255,255,0.08);
    border-left: 3px solid var(--team-primary, #C8102E);
    border-radius: 10px;
    padding: 14px 18px;
    text-align: center;
  }
  .stat-card .label {
    font-size: 11px;
    color: rgba(255,255,255,0.5);
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 4px;
  }
  .stat-card .value {
    font-size: 26px;
    font-weight: 700;
    color: #FAFAFA;
  }
  .section-header {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 8px;
    background: linear-gradient(90deg, var(--team-primary, #C8102E), rgba(255,255,255,0.6));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-weight: 700;
  }
  .chart-card {
    background: linear-gradient(160deg, var(--team-primary-faint, rgba(200,16,46,0.06)) 0%, rgba(13,27,53,0.6) 100%);
    border: 1px solid var(--team-primary-border, rgba(200,16,46,0.25));
    border-radius: 12px;
    padding: 16px;
  }
</style>
""", unsafe_allow_html=True)

seasons = get_available_seasons()
season_labels = {s: f"{str(s)[:4]}-{str(s)[4:]}" for s in seasons}

selected_season = st.sidebar.selectbox(
    "Season", options=seasons,
    format_func=lambda s: season_labels[s], key="pc_season"
)

teams = ["All Teams"] + get_teams(selected_season)
selected_team = st.sidebar.selectbox("Team", options=teams, key="pc_team")

players_df = get_all_players(selected_season)
if selected_team != "All Teams":
    players_df = players_df[players_df["team_abbrev"] == selected_team]

player_options = {
    row.player_id: f"{row.full_name} ({row.team_abbrev})"
    for row in players_df.itertuples()
}

default_id = st.session_state.get("selected_player_id", players_df["player_id"].iloc[0])
default_idx = list(player_options.keys()).index(default_id) if default_id in player_options else 0

selected_player_id = st.sidebar.selectbox(
    "Player", options=list(player_options.keys()),
    format_func=lambda pid: player_options[pid],
    index=default_idx, key="pc_player"
)

stats = get_player_stats(selected_player_id, selected_season)
shots_df = get_player_shots(selected_player_id, selected_season)

if stats is None:
    st.warning("No data found for this player in the selected season.")
    st.stop()

(full_name, position, team_abbrev, headshot_url, team_logo_url,
 games_played, goals, shots_on_goal, sh_pct, total_xg, xg_per_game,
 goals_pctile, sh_pctile, avg_xg_pctile, xg_pg_pctile,
 rush_pctile, dist_pctile) = stats

primary, secondary = team_colors(team_abbrev)
r, g, b = int(primary[1:3], 16), int(primary[3:5], 16), int(primary[5:7], 16)

st.markdown(f"""
<style>
  :root {{
    --team-primary: {primary};
    --team-primary-faint: rgba({r},{g},{b},0.08);
    --team-primary-border: rgba({r},{g},{b},0.3);
  }}
  [data-testid="stSidebar"] {{
    background: linear-gradient(180deg, rgba({r},{g},{b},0.15) 0%, #0E1117 60%);
    border-right: 1px solid rgba({r},{g},{b},0.3);
  }}
</style>
""", unsafe_allow_html=True)

st.markdown(f"""
<div style="
  background: linear-gradient(135deg, {secondary}cc 0%, {primary}55 50%, #0A0E1A 100%);
  border: 1px solid {primary}55;
  border-radius: 14px;
  padding: 20px 28px 20px 20px;
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 8px;
  overflow: visible;
">
  <div style="flex-shrink:0; width:100px; height:100px; border-radius:50%;
              border: 3px solid {primary};
              box-shadow: 0 0 18px {primary}88;
              overflow:hidden; background:#111;
              margin-top: 16px;">
    <img src="{headshot_url}"
         style="width:100%; height:110%; object-fit:cover; object-position: center 20%;" />
  </div>
  <div style="flex:1; min-width:0;">
    <div style="font-size:30px; font-weight:800; color:#FAFAFA; line-height:1.15;
                white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
      {full_name}
    </div>
    <div style="font-size:14px; color:rgba(255,255,255,0.5); margin-top:5px; letter-spacing:0.5px;">
      {position} &nbsp;·&nbsp; {team_abbrev} &nbsp;·&nbsp; {season_labels[selected_season]}
    </div>
  </div>
  <div style="flex-shrink:0; background:rgba(255,255,255,0.07);
              border:1px solid rgba(255,255,255,0.12);
              border-radius:12px; padding:12px 18px;
              display:flex; align-items:center; justify-content:center;">
    <img src="{team_logo_url}" style="height:72px; width:auto; object-fit:contain;" />
  </div>
</div>
""", unsafe_allow_html=True)

c1, c2, c3, c4, c5 = st.columns(5)
for col, label, value in [
    (c1, "Goals",   goals),
    (c2, "SOG",     shots_on_goal),
    (c3, "Sh%",     f"{sh_pct}%"),
    (c4, "xG",      total_xg),
    (c5, "xG / GP", xg_per_game),
]:
    col.markdown(f"""
    <div class="stat-card">
      <div class="label">{label}</div>
      <div class="value">{value}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

with st.expander("Filters", expanded=False):
    f1, f2, f3 = st.columns(3)
    strength_opts = sorted(shots_df["strength"].dropna().unique())
    period_opts   = sorted(shots_df["period"].dropna().unique())
    event_opts    = sorted(shots_df["event_type"].dropna().unique())

    strength_sel = f1.multiselect("Strength",   strength_opts, default=strength_opts)
    period_sel   = f2.multiselect("Period",     period_opts,   default=period_opts)
    event_sel    = f3.multiselect("Event Type", event_opts,    default=event_opts)

filtered_shots = shots_df[
    shots_df["strength"].isin(strength_sel) &
    shots_df["period"].isin(period_sel) &
    shots_df["event_type"].isin(event_sel)
].copy()

mask = filtered_shots["x_coord"] < 0
filtered_shots.loc[mask, "x_coord"] = -filtered_shots.loc[mask, "x_coord"]
filtered_shots.loc[mask, "y_coord"] = -filtered_shots.loc[mask, "y_coord"]

goals_df    = filtered_shots[filtered_shots["event_type"] == "goal"]
nongoals_df = filtered_shots[filtered_shots["event_type"] != "goal"]

map_col, wheel_col = st.columns([2, 2])

with map_col:
    st.markdown(f'<div class="chart-card"><div class="section-header">Shot Map — {len(filtered_shots):,} shots · {len(goals_df)} goals</div>', unsafe_allow_html=True)

    fig_rink = make_rink_figure(height=520)
    xg_vals = nongoals_df["x_goal"].fillna(0).clip(0, 0.5)

    if len(nongoals_df) > 0:
        fig_rink.add_trace(go.Scatter(
            x=nongoals_df["x_coord"],
            y=nongoals_df["y_coord"],
            mode="markers",
            marker=dict(
                color=xg_vals,
                colorscale="Plasma",
                cmin=0, cmax=0.5,
                size=8,
                opacity=0.75,
                colorbar=dict(
                    title=dict(text="xG", font=dict(color="white", size=11)),
                    tickfont=dict(color="white", size=9),
                    thickness=12, len=0.6, x=1.01,
                ),
                line=dict(width=0),
            ),
            customdata=np.column_stack([
                nongoals_df["event_type"],
                nongoals_df["shot_distance"].round(1),
                nongoals_df["shot_angle"].round(1),
                nongoals_df["x_goal"].round(3),
                nongoals_df["strength"],
                nongoals_df["period"],
                nongoals_df["highlight_clip_url"].fillna(""),
            ]),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "Distance: %{customdata[1]} ft<br>"
                "Angle: %{customdata[2]}°<br>"
                "xG: %{customdata[3]}<br>"
                "Strength: %{customdata[4]}<br>"
                "Period: %{customdata[5]}"
                "<extra></extra>"
            ),
            name="Shots",
            showlegend=False,
        ))

    if len(goals_df) > 0:
        fig_rink.add_trace(go.Scatter(
            x=goals_df["x_coord"],
            y=goals_df["y_coord"],
            mode="markers",
            marker=dict(
                symbol="star",
                color=primary,
                size=16,
                opacity=1.0,
                line=dict(color="white", width=1.5),
            ),
            customdata=np.column_stack([
                goals_df["shot_distance"].round(1),
                goals_df["shot_angle"].round(1),
                goals_df["x_goal"].round(3),
                goals_df["strength"],
                goals_df["period"],
                goals_df["highlight_clip_url"].fillna(""),
            ]),
            hovertemplate=(
                "<b>GOAL ⭐</b><br>"
                "Distance: %{customdata[0]} ft<br>"
                "Angle: %{customdata[1]}°<br>"
                "xG: %{customdata[2]}<br>"
                "Strength: %{customdata[3]}<br>"
                "Period: %{customdata[4]}"
                "<extra></extra>"
            ),
            name="Goals",
            showlegend=False,
        ))

    fig_rink.update_layout(clickmode="event")

    clicked = st.plotly_chart(
        fig_rink, use_container_width=True,
        on_select="rerun", key="shot_map"
    )

    st.markdown('</div>', unsafe_allow_html=True)

    if clicked and clicked.get("selection", {}).get("points"):
        point = clicked["selection"]["points"][0]
        cd = point.get("customdata", [])
        clip_url = str(cd[5]) if len(cd) > 5 else ""
        if not clip_url or clip_url in ("", "nan", "None") and len(cd) > 6:
            clip_url = str(cd[6])
        clip_url = clip_url if clip_url not in ("", "nan", "None") else ""
        if clip_url:
            st.session_state["active_video"] = clip_url
        else:
            st.session_state["active_video"] = None
            st.caption("No video available for this shot.")

with wheel_col:
    st.markdown('<div class="chart-card"><div class="section-header">Percentile Ranks vs. League</div>', unsafe_allow_html=True)
    st.caption("Min. 50 shot attempts · Per-game rates (no TOI available)")

    categories = ["Goals/GP", "Sh%", "Avg xG/Shot", "xG/GP", "Rush Shot%", "Shot Distance"]
    values = [
        round((goals_pctile  or 0) * 100),
        round((sh_pctile     or 0) * 100),
        round((avg_xg_pctile or 0) * 100),
        round((xg_pg_pctile  or 0) * 100),
        round((rush_pctile   or 0) * 100),
        round((dist_pctile   or 0) * 100),
    ]

    def pctile_color(v):
        if v >= 67:   return "#FFD700"
        elif v >= 34: return "#F08030"
        else:         return "#4a90d9"

    bar_colors = [pctile_color(v) for v in values]

    wheel = go.Figure()

    for ref in [25, 50, 75]:
        wheel.add_trace(go.Scatterpolar(
            r=[ref] * (len(categories) + 1),
            theta=categories + [categories[0]],
            mode="lines",
            line=dict(color="rgba(255,255,255,0.2)", width=1, dash="dot"),
            showlegend=False,
            hoverinfo="skip",
        ))

    wheel.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor=f"rgba({r},{g},{b},0.18)",
        line=dict(color=primary, width=2),
        mode="lines+markers+text",
        marker=dict(color=bar_colors + [bar_colors[0]], size=10,
                    line=dict(color="white", width=1.5)),
        text=[str(v) for v in values] + [str(values[0])],
        textposition="top center",
        textfont=dict(color="white", size=11, family="monospace"),
        showlegend=False,
    ))

    wheel.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True, range=[0, 100],
                tickvals=[25, 50, 75],
                ticktext=["25", "50", "75"],
                tickfont=dict(size=9, color="rgba(255,255,255,0.3)"),
                gridcolor="rgba(255,255,255,0.08)",
                linecolor="rgba(255,255,255,0.1)",
            ),
            angularaxis=dict(
                tickfont=dict(size=12, color="rgba(255,255,255,0.75)"),
                gridcolor="rgba(255,255,255,0.08)",
                linecolor="rgba(255,255,255,0.1)",
            ),
            bgcolor="#0D1B35",
        ),
        paper_bgcolor="#0A0E1A",
        font_color="white",
        showlegend=False,
        margin=dict(l=55, r=55, t=30, b=30),
        height=380,
    )
    st.plotly_chart(wheel, use_container_width=True)

    for cat, val in zip(categories, values):
        filled = round(val / 10)
        bar = "█" * filled + "░" * (10 - filled)
        color = pctile_color(val)
        st.markdown(
            f"<div style='font-size:12px; margin-bottom:5px; font-family:monospace;'>"
            f"<span style='display:inline-block;width:105px;color:rgba(255,255,255,0.5)'>{cat}</span>"
            f"<span style='color:{color}'>{bar}</span>"
            f"<span style='color:{color}; font-weight:700; margin-left:6px'>{val}</span>"
            f"</div>",
            unsafe_allow_html=True
        )
    st.markdown('</div>', unsafe_allow_html=True)

active_video_sharing_url = st.session_state.get("active_video")
if active_video_sharing_url:
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {secondary}44 0%, #0A0E1A 100%);
        border: 1px solid {primary}44;
        border-radius: 12px;
        padding: 16px 20px;
        margin-top: 8px;
    ">
      <div class="section-header" style="margin-bottom:12px;">Goal Highlight</div>
    </div>
    """, unsafe_allow_html=True)

    with st.spinner("Loading clip..."):
        mp4_url = get_mp4_url(active_video_sharing_url)

    if mp4_url:
        st.video(mp4_url)
    else:
        content_id = active_video_sharing_url.rstrip("/").split("-")[-1]
        brightcove_url = f"https://players.brightcove.net/6415718365001/default_default/index.html?videoId={content_id}"
        st.markdown(f"""
        <div style="position:relative; padding-bottom:56.25%; height:0; border-radius:8px; overflow:hidden;">
          <iframe src="{brightcove_url}"
            style="position:absolute; top:0; left:0; width:100%; height:100%; border:none;"
            allowfullscreen></iframe>
        </div>
        """, unsafe_allow_html=True)
