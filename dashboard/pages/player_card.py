import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from dashboard.components.rink import make_rink_figure
from dashboard.utils.db import (
    get_player_stats, get_player_shots, get_player_game_log,
    get_player_season_log, get_all_players, get_available_seasons, get_teams
)
from dashboard.utils.video import get_video_url
from dashboard.utils.styling import hex_to_rgb, get_performance_color
from dashboard.utils.state import detect_change
from dashboard.utils.data_prep import (
    prepare_filtered_shots, split_shots_by_type, apply_shot_type_filter,
    prepare_shot_type_breakdown, extract_clip_url
)
from dashboard.utils.chart_builders import (
    build_game_log_chart, build_shot_map, build_percentile_wheel, build_shot_type_breakdown,
    build_season_stats_table
)

TEAM_COLORS = {
    "ANA": ("#FC4C02", "#B09862"), "BOS": ("#FFB81C", "#000000"),
    "BUF": ("#FCB514", "#002654"), "CAR": ("#CC0000", "#000000"),
    "CBJ": ("#CE1126", "#002654"), "CGY": ("#C8102E", "#F1BE48"),
    "CHI": ("#CF0A2C", "#000000"), "COL": ("#6F263D", "#236192"),
    "DAL": ("#006847", "#8F8F8C"), "DET": ("#CE1126", "#FFFFFF"),
    "EDM": ("#FF4C00", "#041E42"), "FLA": ("#C8102E", "#041E42"),
    "LAK": ("#A2AAAD", "#111111"), "MIN": ("#154734", "#A6192E"),
    "MTL": ("#AF1E2D", "#192168"), "NJD": ("#CE1126", "#000000"),
    "NSH": ("#FFB81C", "#041E42"), "NYI": ("#00539B", "#F47D30"),
    "NYR": ("#0038A8", "#CE1126"), "OTT": ("#C8102E", "#C69214"),
    "PHI": ("#F74902", "#000000"), "PIT": ("#FCB514", "#000000"),
    "SEA": ("#99D9D9", "#001628"), "SJS": ("#006D75", "#EA7200"),
    "STL": ("#FCB514", "#002F87"), "TBL": ("#1B5299", "#002868"),
    "TOR": ("#2D7DD2", "#003E7E"), "UTA": ("#69B3E7", "#010101"),
    "VAN": ("#00843D", "#00205B"), "VGK": ("#B4975A", "#333F42"),
    "WSH": ("#C8102E", "#041E42"), "WPG": ("#004C97", "#041E42"),
}
DEFAULT_COLORS = ("#C8102E", "#1A1A2E")

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
    position: relative;
    cursor: default;
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
  .stat-card::before {
    content: "i";
    position: absolute;
    top: 6px;
    right: 8px;
    width: 14px;
    height: 14px;
    border-radius: 50%;
    background: rgba(255,255,255,0.15);
    color: rgba(255,255,255,0.5);
    font-size: 9px;
    font-weight: 700;
    font-style: italic;
    font-family: serif;
    line-height: 14px;
    text-align: center;
    transition: background 0.15s, color 0.15s;
  }
  .stat-card:hover::before {
    background: var(--team-primary, #C8102E);
    color: white;
  }
  .stat-card::after {
    content: attr(data-tooltip);
    position: absolute;
    bottom: calc(100% + 8px);
    left: 50%;
    transform: translateX(-50%);
    background: rgba(15,20,35,0.97);
    border: 1px solid rgba(255,255,255,0.15);
    color: rgba(255,255,255,0.85);
    padding: 7px 11px;
    border-radius: 6px;
    font-size: 11px;
    line-height: 1.4;
    white-space: normal;
    width: 200px;
    z-index: 9999;
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.15s;
  }
  .stat-card:hover::after {
    opacity: 1;
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
  div[data-testid="stRadio"] > div { gap: 1px !important; }
  div[data-testid="stRadio"] label {
    padding: 5px 8px !important;
    border-radius: 6px !important;
    transition: background 0.12s !important;
    cursor: pointer !important;
  }
  div[data-testid="stRadio"] label:hover {
    background: rgba(255,255,255,0.07) !important;
  }
  div[data-testid="stRadio"] label > div:first-child { display: none !important; }
  div[data-testid="stRadio"] label > div:last-child p {
    font-family: monospace !important;
    font-size: 12px !important;
    color: rgba(255,255,255,0.6) !important;
    margin: 0 !important;
  }
  div[data-testid="stRadio"] label:has(input:checked) {
    background: var(--team-primary-faint, rgba(200,16,46,0.12)) !important;
    border-left: 2px solid var(--team-primary, #C8102E) !important;
  }
  div[data-testid="stRadio"] label:has(input:checked) > div:last-child p {
    color: rgba(255,255,255,0.95) !important;
    font-weight: 600 !important;
  }
</style>
""", unsafe_allow_html=True)


url_player_id = None
try:
    url_player_id = int(st.query_params.get("player", ""))
except (ValueError, TypeError):
    pass

seasons = get_available_seasons()
season_labels = {s: f"{str(s)[:4]}-{str(s)[4:]}" for s in seasons}

selected_season = st.sidebar.selectbox("Season", options=seasons, format_func=lambda s: season_labels[s], key="pc_season")
teams = ["All Teams"] + get_teams(selected_season)
selected_team = st.sidebar.selectbox("Team", options=teams, key="pc_team")

players_df = get_all_players(selected_season)
if selected_team != "All Teams":
    players_df = players_df[players_df["team_abbrev"] == selected_team]

player_options = {row.player_id: f"{row.full_name} ({row.team_abbrev})" for row in players_df.itertuples()}
default_id = url_player_id if (url_player_id and url_player_id in player_options) else st.session_state.get("selected_player_id", players_df["player_id"].iloc[0])
default_idx = list(player_options.keys()).index(default_id) if default_id in player_options else 0

selected_player_id = st.sidebar.selectbox(
    "Player", options=list(player_options.keys()),
    format_func=lambda pid: player_options[pid],
    index=default_idx, key="pc_player"
)

st.query_params["player"] = str(selected_player_id)

if detect_change("prev_player_id", selected_player_id):
    st.session_state.pop("pc_games", None)
    st.session_state["active_video"] = None
    st.session_state["game_log_game_id"] = None

stats = get_player_stats(selected_player_id, selected_season)
shots_df = get_player_shots(selected_player_id, selected_season)
game_log_df = get_player_game_log(selected_player_id, selected_season)

if stats is None:
    st.warning("No data found for this player in the selected season.")
    st.stop()

primary, secondary = TEAM_COLORS.get(stats[2], DEFAULT_COLORS)
r, g, b = hex_to_rgb(primary)

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

(full_name, position, team_abbrev, headshot_url, team_logo_url,
 games_played, goals, shots_on_goal, sh_pct, total_xg, xg_per_game,
 goals_pctile, sh_pctile, avg_xg_pctile, xg_pg_pctile,
 rebound_pctile, dist_pctile,
 goals_above_expected, gax_pctile) = stats

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
    <img src="{headshot_url}" style="width:100%; height:110%; object-fit:cover; object-position: center 20%;" />
  </div>
  <div style="flex:1; min-width:0;">
    <div style="font-size:30px; font-weight:800; color:#FAFAFA; line-height:1.15;">
      {full_name}
    </div>
    <div style="font-size:14px; color:rgba(255,255,255,0.5); margin-top:5px; letter-spacing:0.5px;">
      {position} · {team_abbrev} · {season_labels[selected_season]}
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

gax_display = f"+{goals_above_expected}" if goals_above_expected and goals_above_expected > 0 else str(goals_above_expected)

stat_cards = [
    ("Goals",              goals,          "Total goals scored (excludes shootout)"),
    ("SOG",                shots_on_goal,  "Shots on goal — shots that required a save or resulted in a goal"),
    ("Sh%",                f"{sh_pct}%",   "Shooting percentage — goals divided by shots on goal"),
    ("xG",                 total_xg,       "Total expected goals — sum of shot quality based on location, type, and context (MoneyPuck model)"),
    ("xG / GP",            xg_per_game,    "Expected goals per game — measures how dangerous a player's shots are on a per game basis"),
    ("Goals Above xG (GAX)", gax_display,  "Goals above expected — positive means the player is finishing better than their shot quality predicts; negative suggests underperformance or bad luck"),
]

cards_html = "".join(
    f'<div class="stat-card" data-tooltip="{tooltip}"><div class="label">{label}</div><div class="value">{value}</div></div>'
    for label, value, tooltip in stat_cards
)
st.markdown(
    f"<div style='display:grid; grid-template-columns: repeat(auto-fill, minmax(140px, 1fr)); gap:12px;'>{cards_html}</div>",
    unsafe_allow_html=True,
)

st.markdown("<div style='margin-top:16px'></div>", unsafe_allow_html=True)

season_log_df = get_player_season_log(selected_player_id)
if len(season_log_df) > 1:
    st.markdown(build_season_stats_table(season_log_df, selected_season, primary, r, g, b), unsafe_allow_html=True)

total_games = len(game_log_df)
if total_games > 1:
    st.sidebar.markdown("---")
    game_options = {
        row.game_id: f"G{row.game_num} {'vs' if row.is_home else 'at'} {row.opponent}  —  {'⭐ ' if row.goals > 0 else ''}{row.goals}G  {row.xg} xG"
        for row in game_log_df.itertuples()
    }
    selected_game_ids_list = st.sidebar.multiselect(
        "Games", options=list(game_options.keys()),
        format_func=lambda gid: game_options[gid],
        default=[], placeholder="All games", key="pc_games"
    )
    selected_game_ids = set(selected_game_ids_list) if selected_game_ids_list else set(game_log_df["game_id"])
    game_filter_active = len(selected_game_ids_list) > 0
else:
    selected_game_ids = set(game_log_df["game_id"])
    game_filter_active = False

strength_opts = sorted(shots_df["strength"].dropna().unique())
period_opts = sorted(shots_df["period"].dropna().unique())
event_opts = sorted(shots_df["event_type"].dropna().unique())
period_label = {1: "P1", 2: "P2", 3: "P3", 4: "OT"}

st.sidebar.markdown("---")
strength_sel = st.sidebar.multiselect("Strength", strength_opts, default=[], placeholder="All strengths")
period_sel = st.sidebar.multiselect("Period", period_opts, default=[], placeholder="All periods", format_func=lambda p: period_label.get(int(p), str(int(p))))
event_sel = st.sidebar.multiselect("Event Type", event_opts, default=[], placeholder="All event types")

log_pts = st.session_state.get("game_log_chart", {}).get("selection", {}).get("points", [])
log_x = int(log_pts[0].get("x", -1)) if log_pts else None

if detect_change("prev_log_x", log_x):
    if log_x is not None:
        game_row = game_log_df[game_log_df["game_num"] == log_x]
        if len(game_row) > 0:
            clicked_game_id = int(game_row.iloc[0]["game_id"])
            st.session_state["game_log_game_id"] = clicked_game_id
            if int(game_row.iloc[0]["goals"]) > 0:
                clips = shots_df[
                    (shots_df["game_id"] == clicked_game_id) &
                    (shots_df["event_type"] == "goal") &
                    shots_df["highlight_clip_url"].notna() &
                    (shots_df["highlight_clip_url"] != "")
                ]["highlight_clip_url"]
                if len(clips) > 0:
                    st.session_state["active_video"] = str(clips.iloc[0])
    else:
        st.session_state["game_log_game_id"] = None

game_log_game_id = st.session_state.get("game_log_game_id")
if game_log_game_id:
    shots_df = shots_df[shots_df["game_id"] == game_log_game_id].copy()
    opp_values = game_log_df[game_log_df["game_id"] == game_log_game_id]["opponent"].values
    opp_label = f" vs {opp_values[0]}" if len(opp_values) > 0 else ""
    st.markdown(f"<div style='font-size:12px; color:rgba(255,255,255,0.45); margin-bottom:8px;'>Showing selected game{opp_label} · stat cards reflect full season</div>", unsafe_allow_html=True)
elif game_filter_active:
    shots_df = shots_df[shots_df["game_id"].isin(selected_game_ids)].copy()
    st.markdown(f"<div style='font-size:12px; color:rgba(255,255,255,0.45); margin-bottom:8px;'>Showing {len(selected_game_ids)} of {total_games} games · stat cards reflect full season</div>", unsafe_allow_html=True)

filtered_shots = prepare_filtered_shots(shots_df, game_log_df, strength_sel, period_sel, event_sel)
goals_df, blocked_df, nongoals_df = split_shots_by_type(filtered_shots)

type_sel = st.session_state.get("shot_type_chart", {}).get("selection", {}).get("points", [])
widget_type = type_sel[0].get("y") if type_sel else None

if detect_change("shot_type_prev", widget_type):
    if widget_type is not None:
        if widget_type == st.session_state.get("selected_shot_type"):
            st.session_state["selected_shot_type"] = None
        else:
            st.session_state["selected_shot_type"] = widget_type

selected_shot_type = st.session_state.get("selected_shot_type")
map_goals_df, map_blocked_df, map_nongoals_df = apply_shot_type_filter(goals_df, blocked_df, nongoals_df, selected_shot_type)

st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
st.markdown('<div class="chart-card"><div class="section-header">Game Log</div>', unsafe_allow_html=True)

fig_log = build_game_log_chart(game_log_df, selected_game_ids, game_filter_active, r, g, b, primary)
st.plotly_chart(fig_log, use_container_width=True, on_select="rerun", key="game_log_chart")

st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
map_col, wheel_col = st.columns([2, 2])

with map_col:
    header_suffix = f" · {selected_shot_type} only" if selected_shot_type else ""
    st.markdown(f'<div class="chart-card"><div class="section-header">Shot Map — {len(filtered_shots):,} shots · {len(goals_df)} goals{header_suffix}</div>', unsafe_allow_html=True)

    fig_rink = build_shot_map(map_nongoals_df, map_blocked_df, map_goals_df, primary)
    clicked = st.plotly_chart(fig_rink, use_container_width=True, on_select="rerun", key="shot_map")

    st.markdown('</div>', unsafe_allow_html=True)

    map_pts = (clicked or {}).get("selection", {}).get("points", [])
    map_key = str(map_pts[0].get("point_index", map_pts[0])) if map_pts else None

    if detect_change("prev_map_key", map_key):
        if map_pts:
            point = map_pts[0]
            cd = point.get("customdata", [])
            clip_url = extract_clip_url(cd)
            if clip_url:
                st.session_state["active_video"] = clip_url
            else:
                st.session_state["active_video"] = None
                st.caption("No video available for this shot.")

with wheel_col:
    st.markdown('<div class="chart-card"><div class="section-header">Percentile Ranks vs. League</div>', unsafe_allow_html=True)
    st.caption("Min. 50 shot attempts")

    categories = ["Goals/GP", "Sh%", "Avg xG/Shot", "xG/GP", "Rebound Shot%", "Shot Distance", "GAX"]
    values = [
        round((goals_pctile or 0) * 100),
        round((sh_pctile or 0) * 100),
        round((avg_xg_pctile or 0) * 100),
        round((xg_pg_pctile or 0) * 100),
        round((rebound_pctile or 0) * 100),
        round((dist_pctile or 0) * 100),
        round((gax_pctile or 0) * 100),
    ]

    fig_wheel = build_percentile_wheel(categories, values, r, g, b, primary)
    st.plotly_chart(fig_wheel, use_container_width=True)

    bar_cols = st.columns(3)
    for i, (cat, val) in enumerate(zip(categories, values)):
        filled = round(val / 10)
        color = get_performance_color(val, {"high": 67, "medium": 34})
        empty_bg = f"repeating-conic-gradient({color} 0% 25%, transparent 0% 50%) 0 0 / 3px 3px"
        total_w = 99
        filled_w = round(filled / 10 * total_w)
        empty_w = total_w - filled_w
        filled_bar = f"<span style='display:inline-block; width:{filled_w}px; height:13px; vertical-align:middle; background:{color};'></span>" if filled_w else ""
        empty_bar = f"<span style='display:inline-block; width:{empty_w}px; height:13px; vertical-align:middle; background:{empty_bg}; filter:brightness(0.5);'></span>" if empty_w else ""
        blocks = filled_bar + empty_bar
        with bar_cols[i % 3]:
            st.markdown(
                f"<div style='font-size:11px; margin-bottom:8px;'>"
                f"<div style='color:rgba(255,255,255,0.5); margin-bottom:2px;'>{cat}</div>"
                f"{blocks}"
                f"<span style='color:{color}; font-weight:700; margin-left:4px; vertical-align:middle;'>{val}</span>"
                f"</div>",
                unsafe_allow_html=True
            )

    st.markdown('</div>', unsafe_allow_html=True)

st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
highlight_col, breakdown_col = st.columns([2, 2])

with highlight_col:
    st.markdown('<div class="chart-card"><div class="section-header">Goal Highlight</div>', unsafe_allow_html=True)

    goal_clips = (
        shots_df[
            (shots_df["event_type"] == "goal") &
            shots_df["highlight_clip_url"].notna() &
            (shots_df["highlight_clip_url"] != "")
        ]
        .merge(game_log_df[["game_id", "game_num", "opponent", "is_home"]], on="game_id", how="left")
        .sort_values(["game_num", "period", "time_in_period"])
        .reset_index(drop=True)
    )

    if len(goal_clips) > 0:
        goal_labels = []
        goal_url_map = {}
        for _, row in goal_clips.iterrows():
            xg_val = f"{round(row['x_goal'], 2)}" if row['x_goal'] else "—"
            date_str = row['game_date'].strftime("%b %d") if row['game_date'] is not None else "—"
            home_away = "vs" if row.get("is_home") else "at"
            label = f"{date_str}  {home_away} {row['opponent']}  ·  P{int(row['period'])} {row['time_in_period']}  ·  {xg_val} xG"
            goal_labels.append(label)
            goal_url_map[label] = row["highlight_clip_url"]

        st.session_state["goal_url_map"] = goal_url_map

        def on_goal_select():
            selected = st.session_state.get("goal_radio")
            url_map = st.session_state.get("goal_url_map", {})
            if selected and selected in url_map:
                st.session_state["active_video"] = url_map[selected]

    active_video_sharing_url = st.session_state.get("active_video")
    if active_video_sharing_url:
        with st.spinner("Loading clip..."):
            video_url = get_video_url(active_video_sharing_url)
        if video_url:
            st.video(video_url)
        else:
            st.markdown(f"""
<div style="position:relative; padding-bottom:56.25%; height:0; border-radius:8px; overflow:hidden;">
  <iframe src="{active_video_sharing_url}" style="position:absolute; top:0; left:0; width:100%; height:100%; border:none;" allowfullscreen></iframe>
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

    if len(goal_clips) > 0:
        st.markdown("<div style='margin-top:4px'></div>", unsafe_allow_html=True)
        with st.container(height=180, border=False):
            st.radio(
                "goals", goal_labels,
                key="goal_radio",
                index=None,
                label_visibility="collapsed",
                on_change=on_goal_select,
            )

    st.markdown('</div>', unsafe_allow_html=True)

with breakdown_col:
    st.markdown('<div class="chart-card"><div class="section-header">Shot Type Breakdown</div>', unsafe_allow_html=True)

    type_df = prepare_shot_type_breakdown(filtered_shots)
    fig_types = build_shot_type_breakdown(type_df, selected_shot_type, r, g, b)
    st.plotly_chart(fig_types, use_container_width=True, on_select="rerun", key="shot_type_chart")

    st.markdown(
        "<div style='font-size:11px; color:rgba(255,255,255,0.35); margin-top:-8px'>"
        "Bar: % of shots · "
        "Dot color: Sh% — "
        "<span style='color:#FFD700'>●</span> ≥15%  "
        "<span style='color:#F08030'>●</span> ≥8%  "
        "<span style='color:#4a90d9'>●</span> &lt;8%  · "
        "Click a bar to filter the shot map"
        "</div>",
        unsafe_allow_html=True
    )
    st.markdown('</div>', unsafe_allow_html=True)
