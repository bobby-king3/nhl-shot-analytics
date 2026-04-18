import duckdb
import streamlit as st
from pathlib import Path

DB_PATH = str(Path(__file__).parent.parent.parent / "data" / "nhl.duckdb")


@st.cache_data(ttl=3600)
def get_league_stats(season: int) -> dict:
    conn = duckdb.connect(DB_PATH, read_only=True)
    row = conn.execute("""
        select
            count(distinct game_id)          as games_played,
            round(avg(goals_per_game) * 2, 2) as avg_goals_per_game,
            round(avg(xg_per_game) * 2, 3)   as avg_xg_per_game,
            round(avg(sh_pct), 1)             as league_sh_pct
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
    conn = duckdb.connect(DB_PATH, read_only=True)
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
            round(m.total_xg, 1)    as total_xg,
            round(m.xg_per_game, 3) as xg_per_game,
            m.xg_per_game_pctile
        from main.mart_player_shooting m
        join main.stg_players p on p.player_id = m.shooter_id
        where m.season = ?
        order by m.total_xg desc
        limit ?
    """, [season, n]).df()
    conn.close()
    return df


@st.cache_data(ttl=3600)
def get_player_stats(player_id: int, season: int):
    conn = duckdb.connect(DB_PATH, read_only=True)
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
            round(m.total_xg, 1)        as total_xg,
            round(m.xg_per_game, 3)     as xg_per_game,
            m.goals_per_game_pctile,
            m.sh_pct_pctile,
            m.avg_xg_per_shot_pctile,
            m.xg_per_game_pctile,
            m.rush_shot_pct_pctile,
            m.shot_distance_pctile
        from main.mart_player_shooting m
        join main.stg_players p on p.player_id = m.shooter_id
        where m.shooter_id = ? and m.season = ?
    """, [player_id, season]).fetchone()
    conn.close()
    return row


@st.cache_data(ttl=3600)
def get_player_shots(player_id: int, season: int):
    conn = duckdb.connect(DB_PATH, read_only=True)
    df = conn.execute("""
        select
            game_id,
            event_type,
            shot_type,
            x_coord,
            y_coord,
            shot_distance,
            shot_angle,
            x_goal,
            strength,
            period,
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
    conn = duckdb.connect(DB_PATH, read_only=True)
    df = conn.execute("""
        with player_games as (
            select
                game_id,
                team_id as player_team_id,
                count(*)                                                              as shots,
                sum(case when event_type = 'goal' then 1 else 0 end)                 as goals,
                round(sum(case when event_type != 'blocked-shot' then coalesce(x_goal, 0) else 0 end), 3) as xg
            from main.mart_shot_events
            where shooter_id = ? and season = ?
              and period < 5
            group by game_id, team_id
        ),
        opponent_teams as (
            select s.game_id, s.team_id as opp_team_id
            from main.mart_shot_events s
            join player_games pg on s.game_id = pg.game_id
            where s.team_id != pg.player_team_id
            group by s.game_id, s.team_id
        ),
        opp_abbrevs as (
            select ot.game_id, any_value(p.team_abbrev) as opponent
            from opponent_teams ot
            join main.stg_players p on p.team_id = ot.opp_team_id
            group by ot.game_id
        )
        select
            pg.game_id,
            row_number() over (order by pg.game_id)  as game_num,
            pg.shots,
            pg.goals,
            pg.xg,
            coalesce(oa.opponent, '???')              as opponent
        from player_games pg
        left join opp_abbrevs oa on oa.game_id = pg.game_id
        order by pg.game_id
    """, [player_id, season]).df()
    conn.close()
    return df


@st.cache_data(ttl=3600)
def get_all_players(season: int):
    conn = duckdb.connect(DB_PATH, read_only=True)
    df = conn.execute("""
        select
            p.player_id,
            p.full_name,
            p.position,
            p.team_abbrev
        from main.mart_player_shooting m
        join main.stg_players p on p.player_id = m.shooter_id
        where m.season = ?
        order by p.last_name
    """, [season]).df()
    conn.close()
    return df


@st.cache_data(ttl=3600)
def get_teams(season: int):
    conn = duckdb.connect(DB_PATH, read_only=True)
    rows = conn.execute("""
        select distinct p.team_abbrev
        from main.mart_player_shooting m
        join main.stg_players p on p.player_id = m.shooter_id
        where m.season = ? and p.team_abbrev is not null
        order by p.team_abbrev
    """, [season]).fetchall()
    conn.close()
    return [r[0] for r in rows]


@st.cache_data(ttl=3600)
def get_available_seasons():
    conn = duckdb.connect(DB_PATH, read_only=True)
    rows = conn.execute("""
        select distinct season from main.mart_player_shooting order by season desc
    """).fetchall()
    conn.close()
    return [r[0] for r in rows]
