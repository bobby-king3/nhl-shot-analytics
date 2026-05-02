import os
import duckdb
import streamlit as st
from pathlib import Path

LOCAL_DB = str(Path(__file__).parent.parent.parent / "data" / "nhl.duckdb")

_env_file = Path(__file__).parent.parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

def connect() -> duckdb.DuckDBPyConnection:
    try:
        token = st.secrets.get("MOTHERDUCK_TOKEN")
    except Exception:
        token = None
    token = token or os.environ.get("MOTHERDUCK_TOKEN")
    if token:
        os.environ.setdefault("motherduck_token", token)
        return duckdb.connect("md:nhl", read_only=True)
    return duckdb.connect(LOCAL_DB, read_only=True)

@st.cache_data(ttl=3600)
def get_league_stats(season: int) -> dict:
    conn = connect()
    row = conn.execute("""
        select
            count(distinct game_id) as games_played,
            round(avg(goals_per_game) * 2, 2) as avg_goals_per_game,
            round(avg(xg_per_game) * 2, 3) as avg_xg_per_game,
            round(avg(sh_pct), 1) as league_sh_pct
        from main.mart_player_shooting
        where season = ?
    """, [season]).fetchone()
    conn.close()
    return {
        "games_played":       row[0],
        "avg_goals_per_game": row[1],
        "avg_xg_per_game":    row[2],
        "league_sh_pct":      row[3],
    }

@st.cache_data(ttl=3600)
def get_leaderboard(season: int, n: int = 20):
    conn = connect()
    df = conn.execute("""
        select
            p.player_id,
            p.full_name,
            p.position,
            p.team_abbrev,
            p.headshot_url,
            p.team_logo_url,
            m.games_played,
            m.goals,
            m.shots_on_goal,
            m.sh_pct,
            round(m.total_xg, 1) as total_xg,
            round(m.xg_per_game, 3) as xg_per_game,
            m.xg_per_game_pctile
        from main.mart_player_shooting m
        join main.mart_players p on p.player_id = m.shooter_id
        where m.season = ?
        order by m.total_xg desc
        limit ?
    """, [season, n]).df()
    conn.close()
    return df

@st.cache_data(ttl=3600)
def get_player_stats(player_id: int, season: int):
    conn = connect()
    row = conn.execute("""
        select
            p.full_name,
            p.position,
            p.team_abbrev,
            p.headshot_url,
            p.team_logo_url,
            m.games_played,
            m.goals,
            m.shots_on_goal,
            m.sh_pct,
            round(m.total_xg, 1) as total_xg,
            round(m.xg_per_game, 3) as xg_per_game,
            m.goals_per_game_pctile,
            m.sh_pct_pctile,
            m.avg_xg_per_shot_pctile,
            m.xg_per_game_pctile,
            m.rebound_shot_pct_pctile,
            m.shot_distance_pctile,
            m.goals_above_expected,
            m.goals_above_expected_pctile,
            p.sweater_number,
            p.height_in,
            p.weight_lbs,
            p.birth_country,
            p.shoots_catches,
            p.birth_date
        from main.mart_player_shooting m
        join main.mart_players p on p.player_id = m.shooter_id
        where m.shooter_id = ? and m.season = ?
    """, [player_id, season]).fetchone()
    conn.close()
    return row


@st.cache_data(ttl=3600)
def get_player_shots(player_id: int, season: int):
    conn = connect()
    df = conn.execute("""
        select
            game_id,
            game_date,
            event_type,
            shot_type,
            x_coord,
            y_coord,
            shot_distance,
            shot_angle,
            x_goal,
            strength,
            period,
            time_in_period,
            is_rush,
            is_rebound,
            highlight_clip_url
        from main.mart_shot_events
        where shooter_id = ? and season = ?
          and x_coord is not null and y_coord is not null
          and period < 5
    """, [player_id, season]).df()
    conn.close()
    return df

@st.cache_data(ttl=3600)
def get_player_game_log(player_id: int, season: int):
    conn = connect()
    df = conn.execute("""
        with player_games as (
            select
                game_id,
                team_id,
                count(*) as shots,
                count(*) filter (where event_type = 'goal') as goals,
                round(sum(coalesce(x_goal, 0)) filter (where event_type != 'blocked-shot'), 3) as xg
            from main.mart_shot_events
            where shooter_id = ? and season = ?
              and period < 5
            group by game_id, team_id
        )
        select
            pg.game_id,
            row_number() over (order by pg.game_id) as game_num,
            pg.shots,
            pg.goals,
            pg.xg,
            tg.opponent_abbrev as opponent,
            tg.is_home,
            tg.game_date
        from player_games pg
        join main.mart_team_games tg
          on tg.game_id = pg.game_id
         and tg.team_id = pg.team_id
        order by pg.game_id
    """, [player_id, season]).df()
    conn.close()
    return df

@st.cache_data(ttl=3600)
def get_all_players(season: int):
    conn = connect()
    df = conn.execute("""
        select
            p.player_id,
            p.full_name,
            p.position,
            p.team_abbrev
        from main.mart_player_shooting m
        join main.mart_players p on p.player_id = m.shooter_id
        where m.season = ?
        order by p.last_name
    """, [season]).df()
    conn.close()
    return df

@st.cache_data(ttl=3600)
def get_teams(season: int):
    conn = connect()
    rows = conn.execute("""
        select distinct p.team_abbrev
        from main.mart_player_shooting m
        join main.mart_players p on p.player_id = m.shooter_id
        where m.season = ? and p.team_abbrev is not null
        order by p.team_abbrev
    """, [season]).fetchall()
    conn.close()
    return [r[0] for r in rows]

@st.cache_data(ttl=3600)
def get_player_season_log(player_id: int):
    conn = connect()
    df = conn.execute("""
        select
            season,
            games_played,
            goals,
            shots_on_goal,
            sh_pct,
            round(total_xg, 1) as total_xg,
            round(xg_per_game, 3) as xg_per_game,
            goals_above_expected
        from main.mart_player_shooting
        where shooter_id = ?
        order by season asc
    """, [player_id]).df()
    conn.close()
    return df

@st.cache_data(ttl=3600)
def get_available_seasons():
    conn = connect()
    rows = conn.execute("""
        select distinct season from main.mart_player_shooting order by season desc
    """).fetchall()
    conn.close()
    return [r[0] for r in rows]

@st.cache_data(ttl=3600)
def get_team_stats(team_abbrev: str, season: int) -> dict:
    conn = connect()
    row = conn.execute("""
        select
            games_played,
            wins,
            losses,
            otl,
            goals_for,
            xg_for,
            sh_pct,
            goals_against,
            xg_against,
            xg_differential,
            sh_pct_sog,
            sv_pct
        from main.mart_team_season
        where team_abbrev = ? and season = ?
    """, [team_abbrev, season]).fetchone()
    conn.close()
    if row is None:
        return {}
    keys = ["games_played", "wins", "losses", "otl", "goals_for", "xg_for",
            "sh_pct", "goals_against", "xg_against", "xg_differential",
            "sh_pct_sog", "sv_pct"]
    return dict(zip(keys, row))


@st.cache_data(ttl=3600)
def get_team_game_log(team_abbrev: str, season: int):
    conn = connect()
    df = conn.execute("""
        select
            game_id,
            row_number() over (order by game_id) as game_num,
            game_date,
            opponent_abbrev as opponent,
            is_home,
            gf,
            ga,
            round(xg_for, 2)     as xg_for,
            round(xg_against, 2) as xg_against,
            result
        from main.mart_team_games
        where team_abbrev = ? and season = ?
        order by game_id
    """, [team_abbrev, season]).df()
    conn.close()
    return df


@st.cache_data(ttl=3600)
def get_all_team_stats(season: int):
    conn = connect()
    df = conn.execute("""
        select
            team_abbrev,
            games_played,
            gf_per_game,
            ga_per_game,
            xg_for_per_game,
            xg_against_per_game,
            xg_diff_per_game,
            sh_pct,
            sh_pct_sog,
            sv_pct
        from main.mart_team_season
        where season = ?
        order by xg_for_per_game desc
    """, [season]).df()
    conn.close()
    return df


@st.cache_data(ttl=3600)
def get_team_roster(team_abbrev: str, season: int):
    conn = connect()
    df = conn.execute("""
        select
            p.player_id,
            p.full_name,
            p.last_name,
            p.position,
            p.headshot_url,
            p.team_logo_url,
            m.games_played,
            m.goals,
            coalesce(m.assists, 0)  as assists,
            coalesce(m.points, 0)  as points,
            m.shots_on_goal,
            m.sh_pct,
            round(m.total_xg, 1) as total_xg,
            round(m.xg_per_game, 3) as xg_per_game,
            m.goals_above_expected  as gax
        from main.mart_player_shooting m
        join main.mart_players p on p.player_id = m.shooter_id
        where p.team_abbrev = ? and m.season = ?
        order by m.total_xg desc
    """, [team_abbrev, season]).df()
    conn.close()
    return df
