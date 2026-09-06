import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import streamlit as st

from dashboard.utils.db import (
    get_available_seasons, get_teams,
    get_team_stats, get_team_game_log, get_team_roster, get_all_team_stats,
)
from dashboard.utils.styling import hex_to_rgb
from dashboard.utils.chart_builders import build_streak_dots_grid, build_team_rolling_xgpct
from dashboard.utils.colors import TEAM_COLORS, DEFAULT_COLORS, TEAM_NAMES

st.markdown("""
<style>
  .block-container {
    padding-top: 1rem !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    max-width: 100% !important;
  }
  .section-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
    letter-spacing: 0.4px;
    margin-bottom: 14px;
    font-weight: 650;
    color: rgba(255,255,255,0.88);
  }
  .section-header::before {
    content: "";
    display: block;
    width: 3px;
    height: 14px;
    border-radius: 1px;
    background: var(--team-primary, #C8102E);
  }
  .chart-card {
    background: #141922;
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 8px;
    padding: 18px;
  }
  .team-metrics {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    margin-top: 14px;
    padding-top: 12px;
    border-top: 1px solid rgba(255,255,255,0.08);
  }
  .team-metric {
    min-width: 0;
    padding: 0 20px;
    border-right: 1px solid rgba(255,255,255,0.1);
  }
  .team-metric:first-child {
    padding-left: 0;
  }
  .team-metric:last-child {
    padding-right: 0;
    border-right: 0;
  }
  .team-metric-value {
    font-size: 18px;
    font-weight: 800;
    line-height: 1.35;
    white-space: nowrap;
  }
  .team-metric-label {
    display: flex;
    align-items: center;
    min-height: 22px;
    color: rgba(255,255,255,0.45);
    font-size: 13px;
    line-height: 1.3;
    white-space: nowrap;
  }
  .team-metric-context {
    margin-top: 1px;
    color: rgba(255,255,255,0.35);
    font-size: 11px;
    line-height: 1.35;
    white-space: nowrap;
  }
  .roster-section {
    background: transparent;
    border: 0;
    padding: 0 0 8px;
  }
  .player-card-chevron {
    position: absolute;
    top: 9px;
    right: 11px;
    color: rgba(255,255,255,0.22);
    font-size: 21px;
    font-weight: 400;
    line-height: 1;
    transition: color 0.15s ease, transform 0.15s ease;
  }
  .player-position {
    display: inline-block;
    flex-shrink: 0;
    padding: 1px 5px;
    border: 1px solid rgba(255,255,255,0.12);
    border-radius: 3px;
    color: rgba(255,255,255,0.46);
    font-size: 9px;
    font-weight: 600;
    line-height: 1.4;
    letter-spacing: 0.5px;
  }
  @media (max-width: 1400px) {
    .team-record {
      width: 100%;
      justify-content: flex-end;
      padding-top: 8px;
    }
  }
</style>
""", unsafe_allow_html=True)

seasons = get_available_seasons()
season_labels = {s: f"{str(s)[:4]}-{str(s)[4:]}" for s in seasons}

url_team   = st.query_params.get("team", None)
url_season = st.query_params.get("season", None)
try:
    url_season = int(url_season) if url_season else None
except ValueError:
    url_season = None

selected_season = st.sidebar.selectbox(
    "Season", options=seasons, format_func=lambda s: season_labels[s],
    index=seasons.index(url_season) if url_season in seasons else 0,
    key="t_season"
)
all_teams = get_teams(selected_season)
selected_team = st.sidebar.selectbox(
    "Team", options=all_teams,
    index=all_teams.index(url_team) if url_team in all_teams else 0,
    key="t_team"
)

st.query_params["team"]   = selected_team
st.query_params["season"] = str(selected_season)

primary, _secondary = TEAM_COLORS.get(selected_team, DEFAULT_COLORS)
r, g, b = hex_to_rgb(primary)

st.markdown(f"""
<style>
  :root {{
    --team-primary: {primary};
    --team-primary-faint: rgba({r},{g},{b},0.08);
    --team-primary-border: rgba({r},{g},{b},0.3);
    --surface: #141922;
    --surface-raised: #191f29;
    --border-subtle: rgba(255,255,255,0.08);
  }}
  [data-testid="stSidebar"] {{
    background: #10141b;
    border-right: 1px solid rgba(255,255,255,0.08);
  }}
  .player-card {{
    transition: transform 0.15s ease, border-color 0.15s ease, background 0.15s ease;
  }}
  .player-card:hover {{
    transform: translateY(-1px);
    background: #1d2430 !important;
    border-color: rgba({r},{g},{b},0.45) !important;
  }}
  .player-card:hover .player-card-chevron {{
    color: {primary};
    transform: translateX(2px);
  }}
</style>
""", unsafe_allow_html=True)

stats       = get_team_stats(selected_team, selected_season)
game_log_df = get_team_game_log(selected_team, selected_season)
roster_df   = get_team_roster(selected_team, selected_season)

all_stats_df = get_all_team_stats(selected_season).copy()
n_teams = len(all_stats_df)

def get_rank(col, ascending=False):
    ranked = all_stats_df[col].rank(ascending=ascending, method="min")
    row = all_stats_df[all_stats_df["team_abbrev"] == selected_team]
    if row.empty:
        return "—"
    return int(ranked[row.index[0]])

gf_rank      = get_rank("gf_per_game")
ga_rank      = get_rank("ga_per_game", ascending=True)
xg_diff_rank = get_rank("xg_diff_per_game")
sh_pct_rank  = get_rank("sh_pct_sog")

def rank_badge(rank):
    if not isinstance(rank, int):
        return ""
    pct = rank / n_teams
    suffix = {1: "st", 2: "nd", 3: "rd"}.get(rank if rank < 20 else rank % 10, "th")
    if pct <= 0.33:
        bg = "rgba(76,175,80,0.15)"; bdr = "rgba(76,175,80,0.45)"; col = "#4CAF50"
    elif pct <= 0.67:
        bg = "rgba(255,255,255,0.07)"; bdr = "rgba(255,255,255,0.14)"; col = "rgba(255,255,255,0.45)"
    else:
        bg = "rgba(200,60,60,0.12)"; bdr = "rgba(200,60,60,0.35)"; col = "rgba(220,100,100,0.85)"
    return (f"<span style='font-size:10px;background:{bg};border:1px solid {bdr};"
            f"border-radius:4px;padding:1px 6px;color:{col};font-weight:700;margin-left:6px;"
            f"vertical-align:middle;'>{rank}{suffix}</span>")

team_name  = TEAM_NAMES.get(selected_team, selected_team)
wins       = stats.get("wins", 0) or 0
losses     = stats.get("losses", 0) or 0
otl        = stats.get("otl", 0) or 0
points     = stats.get("points", 0) or 0
goals_for  = stats.get("goals_for", "—")
goals_ag   = stats.get("goals_against", "—")
xg_for     = stats.get("xg_for", "—")
xg_ag      = stats.get("xg_against", "—")
xg_diff    = stats.get("xg_differential", 0) or 0
sh_pct     = stats.get("sh_pct_sog", "—")
diff_sign  = "+" if xg_diff >= 0 else ""
diff_color = primary if xg_diff >= 0 else "#e05555"

team_logo_url = roster_df.iloc[0]["team_logo_url"] if not roster_df.empty else ""

# MAIN HEADER
gp = stats.get("games_played") or 1
gf_pg  = round(goals_for  / gp, 2) if isinstance(goals_for, (int, float)) else "—"
ga_pg  = round(goals_ag   / gp, 2) if isinstance(goals_ag,  (int, float)) else "—"

st.markdown(f"""
<div class="team-hero" style="
  background: linear-gradient(90deg, #11151d 0%, rgba({r},{g},{b},0.10) 100%);
  border-bottom: 2px solid {primary};
  padding: 24px calc(20px + 1.5rem) 20px calc(20px + 1.5rem);
  margin-left: -1.5rem;
  margin-right: -1.5rem;
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 24px;
  margin-bottom: 0;
">
  <!-- Logo -->
  <div style="flex-shrink:0; background:{'rgba(255,255,255,0.22)' if (0.299*r + 0.587*g + 0.114*b) < 115 else 'rgba(255,255,255,0.04)'}; border-radius:8px;
              padding:16px; border:1px solid rgba(255,255,255,0.08);">
    <img src="{team_logo_url}" style="height:100px; width:auto; object-fit:contain;" />
  </div>

  <!-- Name + season + key stats -->
  <div class="team-identity" style="flex:1; min-width:0;">
    <div style="font-size:36px; font-weight:700; color:#FAFAFA; line-height:1.1;
                letter-spacing:-0.5px;">{team_name}</div>
    <div style="font-size:13px; color:rgba(255,255,255,0.4); margin-top:4px;
                letter-spacing:0.8px;">{season_labels[selected_season]}</div>
    <div class="team-metrics">
      <div class="team-metric">
        <div class="team-metric-value" style="color:{primary};">{goals_for}</div>
        <div class="team-metric-label">GF{rank_badge(gf_rank)}</div>
        <div class="team-metric-context">{xg_for} xG · {gf_pg}/GP</div>
      </div>
      <div class="team-metric">
        <div class="team-metric-value" style="color:rgba(255,255,255,0.65);">{goals_ag}</div>
        <div class="team-metric-label">GA{rank_badge(ga_rank)}</div>
        <div class="team-metric-context">{xg_ag} xG · {ga_pg}/GP</div>
      </div>
      <div class="team-metric">
        <div class="team-metric-value" style="color:{diff_color};">{diff_sign}{xg_diff}</div>
        <div class="team-metric-label">xG Diff{rank_badge(xg_diff_rank)}</div>
        <div class="team-metric-context">xGF − xGA</div>
      </div>
      <div class="team-metric">
        <div class="team-metric-value" style="color:rgba(255,255,255,0.75);">{sh_pct}%</div>
        <div class="team-metric-label">Sh%{rank_badge(sh_pct_rank)}</div>
        <div class="team-metric-context">Goals/Shots on Goal</div>
      </div>
    </div>
  </div>

  <!-- W / L / OTL -->
  <div class="team-record" style="display:flex; gap:0; flex-shrink:0;">
    <div style="text-align:center; padding:0 28px; border-right:1px solid rgba(255,255,255,0.1);">
      <div style="font-size:44px; font-weight:700; color:{primary}; line-height:1;">{wins}</div>
      <div style="font-size:10px; color:rgba(255,255,255,0.35); text-transform:uppercase;
                  letter-spacing:2px; margin-top:4px;">Wins</div>
    </div>
    <div style="text-align:center; padding:0 28px; border-right:1px solid rgba(255,255,255,0.1);">
      <div style="font-size:44px; font-weight:700; color:rgba(255,255,255,0.55); line-height:1;">{losses}</div>
      <div style="font-size:10px; color:rgba(255,255,255,0.35); text-transform:uppercase;
                  letter-spacing:2px; margin-top:4px;">Losses</div>
    </div>
    <div style="text-align:center; padding:0 28px; border-right:1px solid rgba(255,255,255,0.1);">
      <div style="font-size:44px; font-weight:700; color:rgba(255,255,255,0.4); line-height:1;">{otl}</div>
      <div style="font-size:10px; color:rgba(255,255,255,0.35); text-transform:uppercase;
                  letter-spacing:2px; margin-top:4px;">OTL</div>
    </div>
    <div style="text-align:center; padding:0 28px;">
      <div style="font-size:44px; font-weight:700; color:{primary}; line-height:1;">{points}</div>
      <div style="font-size:10px; color:rgba(255,255,255,0.35); text-transform:uppercase;
                  letter-spacing:2px; margin-top:4px;">PTS</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

st.markdown("<div style='padding-top: 28px;'>", unsafe_allow_html=True)

form_col, games_col = st.columns([3, 2])

with form_col:
    legend_html = (
        f"<div style='font-size:11px; color:rgba(255,255,255,0.3); margin-top:8px;'>"
        f"<span style='display:inline-block; width:9px; height:9px; border-radius:50%;"
        f"background:#4CAF50; vertical-align:middle; margin-right:4px;'></span>Win &nbsp;&nbsp;"
        f"<span style='display:inline-block; width:9px; height:9px; border-radius:50%;"
        f"background:rgba(255,200,50,0.85); vertical-align:middle; margin-right:4px;'></span>OT/SO Loss &nbsp;&nbsp;"
        f"<span style='display:inline-block; width:9px; height:9px; border-radius:50%;"
        f"background:#4a4a5a; border:1.5px solid #8B0000;"
        f"vertical-align:middle; margin-right:4px;'></span>Loss"
        f"</div>"
    )
    if not game_log_df.empty:
        grid_html = build_streak_dots_grid(game_log_df)

        def split_record(df):
            w   = (df["result"] == "W").sum()
            l   = (df["result"] == "L").sum()
            otl = (df["result"] == "OTL").sum()
            return w, l, otl

        home_df  = game_log_df[game_log_df["is_home"]]
        away_df  = game_log_df[~game_log_df["is_home"]]
        l10_df   = game_log_df.tail(10)

        hw, hl, hotl = split_record(home_df)
        aw, al, aotl = split_record(away_df)
        l10w, l10l, l10otl = split_record(l10_df)

        splits_html = f"""
        <div style='display:flex; gap:0; margin-top:16px; padding-top:14px;
                    border-top:1px solid rgba(255,255,255,0.07);'>
          <div style='flex:1; text-align:center; padding-right:12px;
                      border-right:1px solid rgba(255,255,255,0.07);'>
            <div style='font-size:10px; color:rgba(255,255,255,0.35); text-transform:uppercase;
                        letter-spacing:1.5px; margin-bottom:6px;'>Home</div>
            <div style='font-size:20px; font-weight:800; color:#FAFAFA; line-height:1;'>{hw}–{hl}–{hotl}</div>
          </div>
          <div style='flex:1; text-align:center; padding: 0 12px;
                      border-right:1px solid rgba(255,255,255,0.07);'>
            <div style='font-size:10px; color:rgba(255,255,255,0.35); text-transform:uppercase;
                        letter-spacing:1.5px; margin-bottom:6px;'>Away</div>
            <div style='font-size:20px; font-weight:800; color:#FAFAFA; line-height:1;'>{aw}–{al}–{aotl}</div>
          </div>
          <div style='flex:1; text-align:center; padding-left:12px;'>
            <div style='font-size:10px; color:rgba(255,255,255,0.35); text-transform:uppercase;
                        letter-spacing:1.5px; margin-bottom:6px;'>Last 10</div>
            <div style='font-size:20px; font-weight:800; color:#FAFAFA; line-height:1;'>{l10w}–{l10l}–{l10otl}</div>
          </div>
        </div>"""

        st.markdown(
            f"<div class='chart-card'><div class='section-header'>Season Performance</div>"
            + grid_html + legend_html + splits_html
            + "</div>",
            unsafe_allow_html=True,
        )

        fig_xg = build_team_rolling_xgpct(game_log_df, r, g, b, primary)
        st.markdown(
            "<div class='chart-card' style='margin-top:14px;'>"
            "<div class='section-header'>Rolling xG% (10-game avg)</div>",
            unsafe_allow_html=True,
        )
        st.plotly_chart(fig_xg, use_container_width=True, config={"displayModeBar": False})

with games_col:
    result_colors = {"W": "#4CAF50", "OTL": "rgba(255,200,50,0.9)", "L": "#e05555"}
    col_header = (
        "<div style='display:flex; align-items:center; gap:10px; padding-bottom:6px;"
        "border-bottom:1px solid rgba(255,255,255,0.1); margin-bottom:2px;'>"
        "<div style='width:32px;'></div>"
        "<div style='flex:1; font-size:10px; color:rgba(255,255,255,0.3); text-transform:uppercase; letter-spacing:1px;'>Opponent</div>"
        "<div style='font-size:10px; color:rgba(255,255,255,0.3); text-transform:uppercase; letter-spacing:1px; width:48px; text-align:right;'>Score</div>"
        "<div style='font-size:10px; color:rgba(255,255,255,0.3); text-transform:uppercase; letter-spacing:1px; width:32px; text-align:right;'>xGF</div>"
        "<div style='font-size:10px; color:rgba(255,255,255,0.3); text-transform:uppercase; letter-spacing:1px; width:32px; text-align:right;'>xGA</div>"
        "<div style='font-size:10px; color:rgba(255,255,255,0.3); text-transform:uppercase; letter-spacing:1px; width:42px; text-align:right;'>Date</div>"
        "</div>"
    )
    rows_html = ""
    if not game_log_df.empty:
        for row in game_log_df.tail(10).iloc[::-1].itertuples():
            res_color   = result_colors.get(row.result, "grey")
            home_away   = "vs" if row.is_home else "at"
            date_str    = row.game_date.strftime("%b %d") if row.game_date is not None else "—"
            xgf_val     = round(row.xg_for, 1)
            xga_val     = round(row.xg_against, 1)
            xgf_color   = primary if xgf_val >= xga_val else "rgba(255,255,255,0.45)"
            xga_color   = "rgba(160,60,60,0.9)" if xga_val > xgf_val else "rgba(255,255,255,0.45)"
            rows_html += (
                f"<div style='display:flex; align-items:center; gap:10px; padding:9px 0;"
                f"border-bottom:1px solid rgba(255,255,255,0.05);'>"
                f"<div style='width:32px; font-size:13px; font-weight:800; color:{res_color};'>{row.result}</div>"
                f"<div style='flex:1; font-size:13px; color:rgba(255,255,255,0.75);'>{home_away} <a href='/?team={row.opponent}&season={selected_season}' target='_self' style='color:rgba(255,255,255,0.75); text-decoration:underline; text-underline-offset:3px;'>{row.opponent}</a></div>"
                f"<div style='font-size:12px; font-family:monospace; color:rgba(255,255,255,0.45); width:48px; text-align:right;'>{int(row.gf)}–{int(row.ga)}</div>"
                f"<div style='font-size:12px; font-family:monospace; color:{xgf_color}; font-weight:700; width:32px; text-align:right;'>{xgf_val}</div>"
                f"<div style='font-size:12px; font-family:monospace; color:{xga_color}; font-weight:700; width:32px; text-align:right;'>{xga_val}</div>"
                f"<div style='font-size:11px; color:rgba(255,255,255,0.25); width:42px; text-align:right;'>{date_str}</div>"
                f"</div>"
            )
    st.markdown(
        "<div class='chart-card'><div class='section-header'>Last 10 Games</div>"
        + col_header
        + rows_html
        + "</div>",
        unsafe_allow_html=True,
    )

st.markdown(
    "<div style='height:1px; background:rgba(255,255,255,0.06); margin-top:28px; margin-bottom:28px;'></div>",
    unsafe_allow_html=True,
)

# ROSTER CARD GRID
SORT_OPTIONS = {"Points": "points", "Goals": "goals", "xG": "total_xg", "Position": "position", "Name": "last_name"}
sort_label = st.selectbox("Sort roster by", options=list(SORT_OPTIONS.keys()), key="roster_sort")
sort_col = SORT_OPTIONS[sort_label]
ascending = sort_col in ("position", "last_name")
roster_df = roster_df.sort_values(sort_col, ascending=ascending)

cards = []
for row in roster_df.itertuples():
    cards.append(
        f"<a href='player_card?player={row.player_id}' target='_self' style='display:block; height:100%; text-decoration:none; color:inherit;'>"
        f"<div class='player-card' style='position:relative; height:100%; box-sizing:border-box; background:#191f29;"
        f"border:1px solid rgba(255,255,255,0.09); border-top:2px solid rgba({r},{g},{b},0.5);"
        f"border-radius:7px; padding:18px 12px 17px; text-align:center; cursor:pointer;'>"
        f"<span class='player-card-chevron' aria-hidden='true'>›</span>"
        f"<img src='{row.headshot_url}' style='width:80px; height:80px; border-radius:50%; object-fit:cover;"
        f"border:1px solid rgba(255,255,255,0.12); margin-bottom:11px;' />"
        f"<div style='display:flex; align-items:center; justify-content:center; flex-wrap:wrap; gap:5px; min-height:34px; margin-bottom:12px;'>"
        f"<span style='font-size:13px; font-weight:700; color:#FAFAFA; line-height:1.25;'>{row.full_name}</span>"
        f"<span class='player-position'>{row.position}</span>"
        f"</div>"
        f"<div style='display:flex; justify-content:center; gap:18px;'>"
        f"<div><div style='font-size:22px; font-weight:700; color:{primary}; line-height:1;'>{int(row.goals)}</div>"
        f"<div style='font-size:9px; color:rgba(255,255,255,0.3); text-transform:uppercase; letter-spacing:1px; margin-top:2px;'>Goals</div></div>"
        f"<div><div style='font-size:22px; font-weight:700; color:rgba(255,255,255,0.85); line-height:1;'>{int(row.points)}</div>"
        f"<div style='font-size:9px; color:rgba(255,255,255,0.3); text-transform:uppercase; letter-spacing:1px; margin-top:2px;'>Points</div></div>"
        f"<div><div style='font-size:22px; font-weight:700; color:rgba(255,255,255,0.5); line-height:1;'>{row.total_xg}</div>"
        f"<div style='font-size:9px; color:rgba(255,255,255,0.3); text-transform:uppercase; letter-spacing:1px; margin-top:2px;'>xG</div></div>"
        f"</div>"
        f"</div></a>"
    )

st.markdown(
    "<div class='roster-section'><div class='section-header'>Roster</div>"
    "<div style='display:grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap:14px;'>"
    + "".join(cards)
    + "</div></div>",
    unsafe_allow_html=True,
)

st.markdown("</div>", unsafe_allow_html=True)
