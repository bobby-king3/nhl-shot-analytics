import streamlit as st
import plotly.graph_objects as go
import numpy as np
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from dashboard.components.rink import make_rink_figure
from dashboard.utils.db import (
    get_player_stats, get_player_shots, get_player_game_log,
    get_all_players, get_available_seasons, get_teams
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

if selected_player_id != st.session_state.get("_prev_player_id"):
    st.session_state["_prev_player_id"] = selected_player_id
    st.session_state.pop("pc_games", None)
    st.session_state["active_video"] = None
    st.session_state["game_log_game_id"] = None

stats = get_player_stats(selected_player_id, selected_season)
shots_df = get_player_shots(selected_player_id, selected_season)
game_log_df = get_player_game_log(selected_player_id, selected_season)

if stats is None:
    st.warning("No data found for this player in the selected season.")
    st.stop()

total_games = len(game_log_df)
if total_games > 1:
    st.sidebar.markdown("---")
    game_options = {
        row.game_id: f"G{row.game_num} vs {row.opponent}  —  {'⭐ ' if row.goals > 0 else ''}{row.goals}G  {row.xg} xG"
        for row in game_log_df.itertuples()
    }
    selected_game_ids_list = st.sidebar.multiselect(
        "Games", options=list(game_options.keys()),
        format_func=lambda gid: game_options[gid],
        default=list(game_options.keys()), key="pc_games"
    )
    selected_game_ids = set(selected_game_ids_list) if selected_game_ids_list else set(game_log_df["game_id"])
    game_filter_active = len(selected_game_ids_list) > 0 and len(selected_game_ids_list) < total_games
else:
    selected_game_ids = set(game_log_df["game_id"])
    game_filter_active = False

_log_pts  = st.session_state.get("game_log_chart", {}).get("selection", {}).get("points", [])
_log_x    = int(_log_pts[0].get("x", -1)) if _log_pts else None
_prev_log_x = st.session_state.get("_prev_log_x")

if _log_x != _prev_log_x:
    st.session_state["_prev_log_x"] = _log_x
    if _log_x is not None:
        _grow = game_log_df[game_log_df["game_num"] == _log_x]
        if len(_grow) > 0:
            _gid = int(_grow.iloc[0]["game_id"])
            st.session_state["game_log_game_id"] = _gid
            if int(_grow.iloc[0]["goals"]) > 0:
                _clips = shots_df[
                    (shots_df["game_id"] == _gid) &
                    (shots_df["event_type"] == "goal") &
                    shots_df["highlight_clip_url"].notna() &
                    (shots_df["highlight_clip_url"] != "")
                ]["highlight_clip_url"]
                if len(_clips) > 0:
                    st.session_state["active_video"] = str(_clips.iloc[0])
    else:
        st.session_state["game_log_game_id"] = None

(full_name, position, team_abbrev, headshot_url, team_logo_url,
 games_played, goals, shots_on_goal, sh_pct, total_xg, xg_per_game,
 goals_pctile, sh_pctile, avg_xg_pctile, xg_pg_pctile,
 rebound_pctile, dist_pctile) = stats

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
  [data-baseweb="tag"] {{
    background-color: rgba({r},{g},{b},0.35) !important;
    border: 1px solid rgba({r},{g},{b},0.7) !important;
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
    <img src="{team_logo_url}" style="height:90px; width:auto; object-fit:contain; image-rendering:high-quality;" />
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

game_log_game_id = st.session_state.get("game_log_game_id")
if game_log_game_id:
    shots_df = shots_df[shots_df["game_id"] == game_log_game_id].copy()
    _opp = game_log_df[game_log_df["game_id"] == game_log_game_id]["opponent"].values
    _opp_label = f" vs {_opp[0]}" if len(_opp) > 0 else ""
    st.markdown(
        f"<div style='font-size:12px; color:rgba(255,255,255,0.45); margin-bottom:8px;'>"
        f"Showing selected game{_opp_label} · stat cards reflect full season</div>",
        unsafe_allow_html=True
    )
elif game_filter_active:
    shots_df = shots_df[shots_df["game_id"].isin(selected_game_ids)].copy()
    st.markdown(
        f"<div style='font-size:12px; color:rgba(255,255,255,0.45); margin-bottom:8px;'>"
        f"Showing {len(selected_game_ids)} of {total_games} games · "
        f"stat cards reflect full season</div>",
        unsafe_allow_html=True
    )

with st.expander("Filters", expanded=False):
    f1, f2, f3 = st.columns(3)
    strength_opts = sorted(shots_df["strength"].dropna().unique())
    period_opts   = sorted(shots_df["period"].dropna().unique())
    event_opts    = sorted(shots_df["event_type"].dropna().unique())

    strength_sel = f1.multiselect("Strength",   strength_opts, default=strength_opts)
    period_label = {1: "P1", 2: "P2", 3: "P3", 4: "OT"}
    period_sel   = f2.multiselect("Period", period_opts, default=period_opts,
                                  format_func=lambda p: period_label.get(int(p), str(int(p))))
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
blocked_df  = filtered_shots[filtered_shots["event_type"] == "blocked-shot"]
nongoals_df = filtered_shots[~filtered_shots["event_type"].isin(["goal", "blocked-shot"])]

_type_sel = st.session_state.get("shot_type_chart", {}).get("selection", {}).get("points", [])
_widget_type = _type_sel[0].get("y") if _type_sel else None
_prev_type = st.session_state.get("_shot_type_prev")

if _widget_type != _prev_type:
    st.session_state["_shot_type_prev"] = _widget_type
    if _widget_type is not None:
        if _widget_type == st.session_state.get("selected_shot_type"):
            st.session_state["selected_shot_type"] = None
        else:
            st.session_state["selected_shot_type"] = _widget_type

selected_shot_type = st.session_state.get("selected_shot_type")

if selected_shot_type:
    map_goals_df    = goals_df[goals_df["shot_type"] == selected_shot_type]
    map_nongoals_df = nongoals_df[nongoals_df["shot_type"] == selected_shot_type]
    map_blocked_df  = blocked_df[blocked_df["shot_type"] == selected_shot_type]
else:
    map_goals_df    = goals_df
    map_nongoals_df = nongoals_df
    map_blocked_df  = blocked_df

st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
st.markdown('<div class="chart-card"><div class="section-header">Game Log</div>', unsafe_allow_html=True)

rolling_avg = game_log_df["xg"].rolling(5, min_periods=1).mean()
goal_games  = game_log_df[game_log_df["goals"] > 0]

bar_colors = [
    f"rgba({r},{g},{b},0.75)" if game_filter_active and gid in selected_game_ids
    else f"rgba({r},{g},{b},0.35)" if game_filter_active
    else f"rgba({r},{g},{b},0.55)"
    for gid in game_log_df["game_id"]
]

fig_log = go.Figure()

fig_log.add_trace(go.Bar(
    x=game_log_df["game_num"],
    y=game_log_df["xg"],
    marker=dict(color=bar_colors, line=dict(width=0)),
    hovertemplate="Game %{x} vs %{customdata}<br>xG: %{y:.3f}<extra></extra>",
    customdata=game_log_df["opponent"],
    showlegend=False,
))

fig_log.add_trace(go.Scatter(
    x=game_log_df["game_num"],
    y=rolling_avg,
    mode="lines",
    line=dict(color="rgba(255,255,255,0.5)", width=2, dash="dot"),
    hovertemplate="Game %{x}<br>5-game avg: %{y:.3f}<extra></extra>",
    showlegend=False,
))

if len(goal_games) > 0:
    fig_log.add_trace(go.Scatter(
        x=goal_games["game_num"],
        y=goal_games["xg"],
        mode="markers",
        marker=dict(symbol="star", color=primary, size=14,
                    line=dict(color="white", width=1.5)),
        hovertemplate="Game %{x}<br>GOAL — xG: %{y:.3f}<extra></extra>",
        showlegend=False,
    ))

if game_filter_active:
    selected_nums = game_log_df[game_log_df["game_id"].isin(selected_game_ids)]["game_num"].tolist()
    for gnum in selected_nums:
        fig_log.add_vrect(
            x0=gnum - 0.5, x1=gnum + 0.5,
            fillcolor=f"rgba({r},{g},{b},0.15)",
            line=dict(width=0),
            layer="below",
        )

fig_log.update_xaxes(
    showgrid=False, zeroline=False,
    tickfont=dict(color="rgba(255,255,255,0.4)", size=10),
    title=dict(text="Game", font=dict(color="rgba(255,255,255,0.4)", size=11)),
    fixedrange=True,
)
fig_log.update_yaxes(
    showgrid=True, gridcolor="rgba(255,255,255,0.06)",
    zeroline=False, tickfont=dict(color="rgba(255,255,255,0.4)", size=10),
    title=dict(text="xG", font=dict(color="rgba(255,255,255,0.4)", size=11)),
    fixedrange=True,
)
fig_log.update_layout(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=40, r=20, t=10, b=30),
    height=220,
    bargap=0.15,
)

st.plotly_chart(fig_log, use_container_width=True, on_select="rerun", key="game_log_chart")

st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
map_col, wheel_col = st.columns([2, 2])

with map_col:
    header_suffix = f" · {selected_shot_type} only" if selected_shot_type else ""
    st.markdown(f'<div class="chart-card"><div class="section-header">Shot Map — {len(filtered_shots):,} shots · {len(goals_df)} goals{header_suffix}</div>', unsafe_allow_html=True)

    fig_rink = make_rink_figure(height=520)
    xg_vals = map_nongoals_df["x_goal"].fillna(0).clip(0, 0.5)

    if len(map_nongoals_df) > 0:
        fig_rink.add_trace(go.Scatter(
            x=map_nongoals_df["x_coord"],
            y=map_nongoals_df["y_coord"],
            mode="markers",
            marker=dict(
                color=xg_vals,
                colorscale="RdBu_r",
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
                map_nongoals_df["event_type"],
                map_nongoals_df["shot_distance"].round(1),
                map_nongoals_df["shot_angle"].round(1),
                map_nongoals_df["x_goal"].round(3),
                map_nongoals_df["strength"],
                map_nongoals_df["period"],
                map_nongoals_df["highlight_clip_url"].fillna(""),
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

    if len(map_blocked_df) > 0:
        fig_rink.add_trace(go.Scatter(
            x=map_blocked_df["x_coord"],
            y=map_blocked_df["y_coord"],
            mode="markers",
            marker=dict(
                symbol="x",
                color="rgba(255,255,255,0.25)",
                size=6,
                line=dict(width=1, color="rgba(255,255,255,0.25)"),
            ),
            customdata=np.column_stack([
                map_blocked_df["shot_distance"].round(1),
                map_blocked_df["shot_angle"].round(1),
                map_blocked_df["strength"],
                map_blocked_df["period"],
            ]),
            hovertemplate=(
                "<b>Blocked Shot</b><br>"
                "Distance: %{customdata[0]} ft<br>"
                "Angle: %{customdata[1]}°<br>"
                "Strength: %{customdata[2]}<br>"
                "Period: %{customdata[3]}"
                "<extra></extra>"
            ),
            name="Blocked",
            showlegend=False,
        ))

    if len(map_goals_df) > 0:
        fig_rink.add_trace(go.Scatter(
            x=map_goals_df["x_coord"],
            y=map_goals_df["y_coord"],
            mode="markers",
            marker=dict(
                symbol="star",
                color=primary,
                size=16,
                opacity=1.0,
                line=dict(color="white", width=1.5),
            ),
            customdata=np.column_stack([
                map_goals_df["shot_distance"].round(1),
                map_goals_df["shot_angle"].round(1),
                map_goals_df["x_goal"].round(3),
                map_goals_df["strength"],
                map_goals_df["period"],
                map_goals_df["highlight_clip_url"].fillna(""),
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
    st.caption("Min. 50 shot attempts")

    categories = ["Goals/GP", "Sh%", "Avg xG/Shot", "xG/GP", "Rebound Shot%", "Shot Distance"]
    values = [
        round((goals_pctile   or 0) * 100),
        round((sh_pctile      or 0) * 100),
        round((avg_xg_pctile  or 0) * 100),
        round((xg_pg_pctile   or 0) * 100),
        round((rebound_pctile or 0) * 100),
        round((dist_pctile    or 0) * 100),
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

    bar_cols = st.columns(3)
    for i, (cat, val) in enumerate(zip(categories, values)):
        filled = round(val / 10)
        bar = "█" * filled + "░" * (10 - filled)
        color = pctile_color(val)
        with bar_cols[i % 3]:
            st.markdown(
                f"<div style='font-size:11px; margin-bottom:8px; font-family:monospace;'>"
                f"<div style='color:rgba(255,255,255,0.5); margin-bottom:2px;'>{cat}</div>"
                f"<span style='color:{color}'>{bar}</span>"
                f"<span style='color:{color}; font-weight:700; margin-left:4px'>{val}</span>"
                f"</div>",
                unsafe_allow_html=True
            )
    st.markdown('</div>', unsafe_allow_html=True)

# ── Goal Highlight + Shot Type Breakdown ─────────────────────────────────────
st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
highlight_col, breakdown_col = st.columns([2, 2])

with highlight_col:
    st.markdown('<div class="chart-card"><div class="section-header">Goal Highlight</div>', unsafe_allow_html=True)

    active_video_sharing_url = st.session_state.get("active_video")
    if active_video_sharing_url:
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
    else:
        st.markdown("""
<div style="
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    padding: 32px 16px; border-radius:8px;
    background:rgba(255,255,255,0.03); border:1px dashed rgba(255,255,255,0.12);
    color:rgba(255,255,255,0.3); font-size:13px; text-align:center; gap:8px;
">
  <div style="font-size:28px;">▶</div>
  <div>Click a goal on the shot map or game log to load highlight</div>
</div>
""", unsafe_allow_html=True)

    goal_clips = (
        shots_df[
            (shots_df["event_type"] == "goal") &
            shots_df["highlight_clip_url"].notna() &
            (shots_df["highlight_clip_url"] != "")
        ]
        .merge(game_log_df[["game_id", "game_num", "opponent"]], on="game_id", how="left")
        .sort_values(["game_num", "period", "time_in_period"])
        .reset_index(drop=True)
    )

    if len(goal_clips) > 0:
        st.markdown("<div style='margin-top:4px'></div>", unsafe_allow_html=True)
        with st.container(height=180, border=False):
            for i, row in goal_clips.iterrows():
                xg_val = f"{round(row['x_goal'], 2)}" if row['x_goal'] else "—"
                date_str = row['game_date'].strftime("%b %d") if row['game_date'] is not None else "—"
                label = f"{date_str}  vs {row['opponent']}  ·  P{int(row['period'])} {row['time_in_period']}  ·  {xg_val} xG"
                if st.button(label, key=f"goal_btn_{i}", use_container_width=True):
                    st.session_state["active_video"] = row["highlight_clip_url"]

    st.markdown('</div>', unsafe_allow_html=True)

with breakdown_col:
    st.markdown('<div class="chart-card"><div class="section-header">Shot Type Breakdown</div>', unsafe_allow_html=True)

    type_df = (
        filtered_shots[filtered_shots["shot_type"].notna()]
        .groupby("shot_type")
        .agg(shots=("event_type", "count"), goals=("event_type", lambda x: (x == "goal").sum()))
        .reset_index()
        .assign(
            shots=lambda d: d["shots"].astype(int),
            goals=lambda d: d["goals"].astype(int),
            sh_pct=lambda d: (d["goals"].astype(float) / d["shots"].astype(float) * 100).round(1)
        )
        .sort_values("shots", ascending=True)
    )

    def sh_pct_color(v):
        if v >= 15:   return "#FFD700"
        elif v >= 8:  return "#F08030"
        else:         return "#4a90d9"

    dot_colors = [sh_pct_color(v) for v in type_df["sh_pct"]]

    bar_fill_colors = [
        f"rgba({r},{g},{b},0.7)" if t == selected_shot_type else f"rgba({r},{g},{b},0.3)"
        for t in type_df["shot_type"]
    ]
    bar_line_colors = [
        f"rgba({r},{g},{b},1.0)" if t == selected_shot_type else f"rgba({r},{g},{b},0.6)"
        for t in type_df["shot_type"]
    ]

    fig_types = go.Figure()

    fig_types.add_trace(go.Bar(
        x=type_df["shots"],
        y=type_df["shot_type"],
        orientation="h",
        marker=dict(
            color=bar_fill_colors,
            line=dict(color=bar_line_colors, width=1),
        ),
        text=type_df["shots"],
        textposition="outside",
        textfont=dict(color="rgba(255,255,255,0.6)", size=11),
        hovertemplate="<b>%{y}</b><br>Shots: %{x}<extra></extra>",
        showlegend=False,
    ))

    fig_types.add_trace(go.Scatter(
        x=type_df["shots"],
        y=type_df["shot_type"],
        mode="markers+text",
        marker=dict(color=dot_colors, size=10, line=dict(color="white", width=1.5)),
        text=[f"{v}%" for v in type_df["sh_pct"]],
        textposition="middle right",
        textfont=dict(color="rgba(255,255,255,0.75)", size=10),
        hovertemplate="<b>%{y}</b><br>Sh%: %{text}<extra></extra>",
        showlegend=False,
    ))

    fig_types.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, fixedrange=True)
    fig_types.update_yaxes(showgrid=False, zeroline=False, fixedrange=True,
                            tickfont=dict(color="rgba(255,255,255,0.75)", size=12))
    fig_types.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=60, t=10, b=10),
        height=280,
        bargap=0.3,
    )

    st.plotly_chart(fig_types, use_container_width=True, on_select="rerun", key="shot_type_chart")

    st.markdown(
        "<div style='font-size:11px; color:rgba(255,255,255,0.35); margin-top:-8px'>"
        "Dot color: Sh% — "
        "<span style='color:#FFD700'>●</span> ≥15%  "
        "<span style='color:#F08030'>●</span> ≥8%  "
        "<span style='color:#4a90d9'>●</span> &lt;8%  · "
        "Click a bar to filter the shot map"
        "</div>",
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)
