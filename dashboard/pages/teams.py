import streamlit as st
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent.parent))

from dashboard.utils.db import (
    get_available_seasons, get_teams,
    get_team_stats, get_team_game_log, get_team_roster, get_all_team_stats,
)
from dashboard.utils.styling import hex_to_rgb
from dashboard.utils.chart_builders import build_streak_dots_grid, build_team_rolling_xgpct

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

TEAM_NAMES = {
    "ANA": "Anaheim Ducks", "BOS": "Boston Bruins", "BUF": "Buffalo Sabres",
    "CAR": "Carolina Hurricanes", "CBJ": "Columbus Blue Jackets", "CGY": "Calgary Flames",
    "CHI": "Chicago Blackhawks", "COL": "Colorado Avalanche", "DAL": "Dallas Stars",
    "DET": "Detroit Red Wings", "EDM": "Edmonton Oilers", "FLA": "Florida Panthers",
    "LAK": "Los Angeles Kings", "MIN": "Minnesota Wild", "MTL": "Montréal Canadiens",
    "NJD": "New Jersey Devils", "NSH": "Nashville Predators", "NYI": "New York Islanders",
    "NYR": "New York Rangers", "OTT": "Ottawa Senators", "PHI": "Philadelphia Flyers",
    "PIT": "Pittsburgh Penguins", "SEA": "Seattle Kraken", "SJS": "San Jose Sharks",
    "STL": "St. Louis Blues", "TBL": "Tampa Bay Lightning", "TOR": "Toronto Maple Leafs",
    "UTA": "Utah Mammoth", "VAN": "Vancouver Canucks", "VGK": "Vegas Golden Knights",
    "WSH": "Washington Capitals", "WPG": "Winnipeg Jets",
}

st.markdown("""
<style>
  .block-container {
    padding-top: 0 !important;
    padding-left: 1.5rem !important;
    padding-right: 1.5rem !important;
    max-width: 100% !important;
  }
  .section-header {
    font-size: 12px;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-bottom: 12px;
    font-weight: 700;
    background: linear-gradient(90deg, var(--team-primary, #C8102E), rgba(255,255,255,0.6));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
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
selected_season = st.sidebar.selectbox("Season", options=seasons, format_func=lambda s: season_labels[s], key="t_season")
all_teams = get_teams(selected_season)
selected_team = st.sidebar.selectbox("Team", options=all_teams, key="t_team")

primary, secondary = TEAM_COLORS.get(selected_team, DEFAULT_COLORS)
r, g, b = hex_to_rgb(primary)

st.markdown(f"""
<style>
  :root {{
    --team-primary: {primary};
    --team-primary-faint: rgba({r},{g},{b},0.08);
    --team-primary-border: rgba({r},{g},{b},0.3);
  }}
  [data-testid="stSidebar"] {{
    background: linear-gradient(180deg, rgba({r},{g},{b},0.18) 0%, #0E1117 60%);
    border-right: 1px solid rgba({r},{g},{b},0.3);
  }}
  .player-card {{
    transition: transform 0.15s ease, border-color 0.15s ease, background 0.15s ease;
  }}
  .player-card:hover {{
    transform: translateY(-3px);
    background: rgba({r},{g},{b},0.15) !important;
    border-color: rgba({r},{g},{b},0.55) !important;
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
goals_for  = stats.get("goals_for", "—")
goals_ag   = stats.get("goals_against", "—")
xg_for     = stats.get("xg_for", "—")
xg_ag      = stats.get("xg_against", "—")
xg_diff    = stats.get("xg_differential", 0) or 0
sh_pct     = stats.get("sh_pct_sog", "—")
diff_sign  = "+" if xg_diff >= 0 else ""
diff_color = primary if xg_diff >= 0 else "#e05555"

team_logo_url = roster_df.iloc[0]["team_logo_url"] if not roster_df.empty else ""

# ── HERO HEADER ──────────────────────────────────────────────────────────────
gp = stats.get("games_played") or 1
gf_pg  = round(goals_for  / gp, 2) if isinstance(goals_for, (int, float)) else "—"
ga_pg  = round(goals_ag   / gp, 2) if isinstance(goals_ag,  (int, float)) else "—"

st.markdown(f"""
<div style="
  background: linear-gradient(135deg, #0A0E1A 0%, rgba({r},{g},{b},0.25) 50%, {secondary}99 100%);
  border-bottom: 3px solid {primary};
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
  <div style="flex-shrink:0; background:rgba(255,255,255,0.06); border-radius:16px;
              padding:16px; border:1px solid rgba(255,255,255,0.08);">
    <img src="{team_logo_url}" style="height:100px; width:auto; object-fit:contain;" />
  </div>

  <!-- Name + season + key stats -->
  <div style="flex:1; min-width:0;">
    <div style="font-size:42px; font-weight:900; color:#FAFAFA; line-height:1.05;
                letter-spacing:-1px;">{team_name}</div>
    <div style="font-size:13px; color:rgba(255,255,255,0.4); margin-top:4px;
                letter-spacing:2px; text-transform:uppercase;">{season_labels[selected_season]}</div>
    <div style="display:flex; gap:0; margin-top:14px; border-top:1px solid rgba(255,255,255,0.08); padding-top:12px;">
      <div style="padding-right:20px; border-right:1px solid rgba(255,255,255,0.1);">
        <div style="font-size:18px; font-weight:800; color:{primary};">{goals_for} <span style="font-size:13px; color:rgba(255,255,255,0.5); font-weight:400;">GF</span>{rank_badge(gf_rank)}</div>
        <div style="font-size:11px; color:rgba(255,255,255,0.35); margin-top:1px;">{xg_for} xG · {gf_pg}/GP</div>
      </div>
      <div style="padding:0 20px; border-right:1px solid rgba(255,255,255,0.1);">
        <div style="font-size:18px; font-weight:800; color:rgba(255,255,255,0.65);">{goals_ag} <span style="font-size:13px; color:rgba(255,255,255,0.4); font-weight:400;">GA</span>{rank_badge(ga_rank)}</div>
        <div style="font-size:11px; color:rgba(255,255,255,0.35); margin-top:1px;">{xg_ag} xG · {ga_pg}/GP</div>
      </div>
      <div style="padding:0 20px; border-right:1px solid rgba(255,255,255,0.1);">
        <div style="font-size:18px; font-weight:800; color:{diff_color};">{diff_sign}{xg_diff} <span style="font-size:13px; color:rgba(255,255,255,0.4); font-weight:400;">xG Diff</span>{rank_badge(xg_diff_rank)}</div>
        <div style="font-size:11px; color:rgba(255,255,255,0.35); margin-top:1px;">expected goals differential</div>
      </div>
      <div style="padding-left:20px;">
        <div style="font-size:18px; font-weight:800; color:rgba(255,255,255,0.75);">{sh_pct}% <span style="font-size:13px; color:rgba(255,255,255,0.4); font-weight:400;">Sh%</span>{rank_badge(sh_pct_rank)}</div>
        <div style="font-size:11px; color:rgba(255,255,255,0.35); margin-top:1px;">goals / shots on goal</div>
      </div>
    </div>
  </div>

  <!-- Divider -->
  <div style="width:1px; height:80px; background:rgba(255,255,255,0.12); flex-shrink:0;"></div>

  <!-- W / L / OTL -->
  <div style="display:flex; gap:0; flex-shrink:0;">
    <div style="text-align:center; padding:0 28px; border-right:1px solid rgba(255,255,255,0.1);">
      <div style="font-size:56px; font-weight:900; color:{primary}; line-height:1;">{wins}</div>
      <div style="font-size:10px; color:rgba(255,255,255,0.35); text-transform:uppercase;
                  letter-spacing:2px; margin-top:4px;">Wins</div>
    </div>
    <div style="text-align:center; padding:0 28px; border-right:1px solid rgba(255,255,255,0.1);">
      <div style="font-size:56px; font-weight:900; color:rgba(255,255,255,0.45); line-height:1;">{losses}</div>
      <div style="font-size:10px; color:rgba(255,255,255,0.35); text-transform:uppercase;
                  letter-spacing:2px; margin-top:4px;">Losses</div>
    </div>
    <div style="text-align:center; padding:0 28px;">
      <div style="font-size:56px; font-weight:900; color:rgba(255,255,255,0.25); line-height:1;">{otl}</div>
      <div style="font-size:10px; color:rgba(255,255,255,0.35); text-transform:uppercase;
                  letter-spacing:2px; margin-top:4px;">OTL</div>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

# ── MAIN CONTENT ─────────────────────────────────────────────────────────────
st.markdown("<div style='padding-top: 28px;'>", unsafe_allow_html=True)

# ── SEASON FORM + LAST 5 ─────────────────────────────────────────────────────
form_col, games_col = st.columns([3, 2])

with form_col:
    legend_html = (
        f"<div style='font-size:11px; color:rgba(255,255,255,0.3); margin-top:8px;'>"
        f"<span style='display:inline-block; width:9px; height:9px; border-radius:50%;"
        f"background:#4CAF50; vertical-align:middle; margin-right:4px;'></span>Win &nbsp;&nbsp;"
        f"<span style='display:inline-block; width:9px; height:9px; border-radius:50%;"
        f"background:rgba(255,200,50,0.85); vertical-align:middle; margin-right:4px;'></span>OT/SO Loss &nbsp;&nbsp;"
        f"<span style='display:inline-block; width:9px; height:9px; border-radius:50%;"
        f"background:rgba(40,40,55,0.9); border:1.5px solid rgba(120,120,140,0.5);"
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
    result_colors = {"W": primary, "OTL": "rgba(255,200,50,0.9)", "L": "rgba(160,60,60,0.8)"}
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
                f"<div style='flex:1; font-size:13px; color:rgba(255,255,255,0.75);'>{home_away} {row.opponent}</div>"
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

# ── ROSTER CARD GRID ─────────────────────────────────────────────────────────
cards = []
for row in roster_df.itertuples():
    cards.append(
        f"<a href='player_card?player={row.player_id}' target='_self' style='text-decoration:none; color:inherit;'>"
        f"<div class='player-card' style='background:rgba({r},{g},{b},0.07); border:1px solid rgba({r},{g},{b},0.22);"
        f"border-radius:12px; padding:18px 12px 14px 12px; text-align:center; cursor:pointer;'>"
        f"<img src='{row.headshot_url}' style='width:72px; height:72px; border-radius:50%; object-fit:cover;"
        f"border:2px solid rgba({r},{g},{b},0.45); margin-bottom:10px;' />"
        f"<div style='font-size:13px; font-weight:700; color:#FAFAFA; line-height:1.2; margin-bottom:3px;'>{row.full_name}</div>"
        f"<div style='font-size:10px; color:rgba(255,255,255,0.35); text-transform:uppercase; letter-spacing:1.5px; margin-bottom:12px;'>{row.position}</div>"
        f"<div style='display:flex; justify-content:center; gap:18px; margin-bottom:14px;'>"
        f"<div><div style='font-size:22px; font-weight:900; color:{primary}; line-height:1;'>{int(row.goals)}</div>"
        f"<div style='font-size:9px; color:rgba(255,255,255,0.3); text-transform:uppercase; letter-spacing:1px; margin-top:2px;'>Goals</div></div>"
        f"<div><div style='font-size:22px; font-weight:900; color:rgba(255,255,255,0.85); line-height:1;'>{int(row.points)}</div>"
        f"<div style='font-size:9px; color:rgba(255,255,255,0.3); text-transform:uppercase; letter-spacing:1px; margin-top:2px;'>Points</div></div>"
        f"<div><div style='font-size:22px; font-weight:900; color:rgba(255,255,255,0.5); line-height:1;'>{row.total_xg}</div>"
        f"<div style='font-size:9px; color:rgba(255,255,255,0.3); text-transform:uppercase; letter-spacing:1px; margin-top:2px;'>xG</div></div>"
        f"</div>"
        f"<div style='font-size:11px; font-weight:600; color:{primary}; border:1px solid rgba({r},{g},{b},0.4);"
        f"border-radius:5px; padding:5px 0;'>View Player Card →</div>"
        f"</div></a>"
    )

st.markdown(
    "<div class='chart-card'><div class='section-header'>Roster</div>"
    "<div style='display:grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap:14px;'>"
    + "".join(cards)
    + "</div></div>",
    unsafe_allow_html=True,
)

st.markdown("</div>", unsafe_allow_html=True)
