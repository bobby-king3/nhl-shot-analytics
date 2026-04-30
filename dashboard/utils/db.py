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
            round(m.total_xg, 1)        as total_xg,
            round(m.xg_per_game, 3)     as xg_per_game,
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
            p.shoots_catches
        from main.mart_player_shooting m
        join main.stg_players p on p.player_id = m.shooter_id
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
            coalesce(oa.opponent, '???')              as opponent,
            g.home_team_id = pg.player_team_id        as is_home,
            g.game_date                               as game_date
        from player_games pg
        left join opp_abbrevs oa on oa.game_id = pg.game_id
        left join main.stg_games g on g.game_id = pg.game_id
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
        join main.stg_players p on p.player_id = m.shooter_id
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
        join main.stg_players p on p.player_id = m.shooter_id
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
            round(total_xg, 1)       as total_xg,
            round(xg_per_game, 3)    as xg_per_game,
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
        with team_games as (
            select
                game_id,
                case when home_team_abbrev = ? then home_team_id else away_team_id end as team_id,
                case when home_team_abbrev = ? then home_score  else away_score  end as gf,
                case when home_team_abbrev = ? then away_score  else home_score  end as ga,
                home_team_abbrev = ?                                                  as is_home,
                home_win,
                last_period_type
            from main.stg_games
            where (home_team_abbrev = ? or away_team_abbrev = ?) and season = ?
        ),
        shots_for as (
            select
                sum(case when se.event_type = 'goal'           then 1 else 0 end) as goals_for,
                sum(case when se.event_type != 'blocked-shot'  then coalesce(se.x_goal, 0) else 0 end) as xg_for,
                count(*) as shots_for,
                sum(case when se.event_type in ('shot-on-goal', 'goal') then 1 else 0 end) as sog_for
            from main.mart_shot_events se
            join team_games tg on tg.game_id = se.game_id and tg.team_id = se.team_id
            where se.period < 5
        ),
        shots_against as (
            select
                sum(case when se.event_type = 'goal'           then 1 else 0 end) as goals_against,
                sum(case when se.event_type != 'blocked-shot'  then coalesce(se.x_goal, 0) else 0 end) as xg_against,
                sum(case when se.event_type in ('shot-on-goal', 'goal') then 1 else 0 end) as sog_against
            from main.mart_shot_events se
            join team_games tg on tg.game_id = se.game_id and tg.team_id != se.team_id
            where se.period < 5
        ),
        record as (
            select
                count(*) as games_played,
                sum(case when (    is_home and     home_win)
                           or (not is_home and not home_win) then 1 else 0 end) as wins,
                sum(case when last_period_type != 'REG'
                           and ((    is_home and not home_win)
                                or (not is_home and     home_win)) then 1 else 0 end) as otl,
                sum(case when last_period_type  = 'REG'
                           and ((    is_home and not home_win)
                                or (not is_home and     home_win)) then 1 else 0 end) as losses
            from team_games
        )
        select
            r.games_played,
            r.wins,
            r.losses,
            r.otl,
            sf.goals_for,
            round(sf.xg_for, 1)                                                       as xg_for,
            round(sf.goals_for * 1.0 / nullif(sf.shots_for, 0) * 100, 1)             as sh_pct,
            sa.goals_against,
            round(sa.xg_against, 1)                                                   as xg_against,
            round(sf.xg_for - sa.xg_against, 1)                                       as xg_differential,
            round(sf.goals_for * 1.0 / nullif(sf.sog_for, 0) * 100, 1)               as sh_pct_sog,
            round((1.0 - sa.goals_against * 1.0 / nullif(sa.sog_against, 0)) * 100, 1) as sv_pct
        from record r, shots_for sf, shots_against sa
    """, [team_abbrev] * 6 + [season]).fetchone()
    conn.close()
    if row is None:
        return {}
    keys = ["games_played", "wins", "losses", "otl", "goals_for", "xg_for",
            "sh_pct", "goals_against", "xg_against", "xg_differential",
            "sh_pct_sog", "sv_pct"]
    return dict(zip(keys, row))


@st.cache_data(ttl=3600)
def get_team_shots(team_abbrev: str, season: int):
    conn = connect()
    df = conn.execute("""
        with team_games as (
            select
                game_id,
                case when home_team_abbrev = ? then home_team_id else away_team_id end as team_id
            from main.stg_games
            where (home_team_abbrev = ? or away_team_abbrev = ?) and season = ?
        )
        select
            se.x_coord,
            se.y_coord,
            se.event_type,
            se.shot_type,
            se.x_goal,
            se.strength
        from main.mart_shot_events se
        join team_games tg on tg.game_id = se.game_id and tg.team_id = se.team_id
        where se.period < 5
          and se.x_coord is not null and se.y_coord is not null
    """, [team_abbrev] * 3 + [season]).df()
    conn.close()
    return df


@st.cache_data(ttl=3600)
def get_team_game_log(team_abbrev: str, season: int):
    conn = connect()
    df = conn.execute("""
        with team_games as (
            select
                g.game_id,
                g.game_date,
                g.last_period_type,
                g.home_win,
                case when g.home_team_abbrev = ? then g.home_team_id  else g.away_team_id  end as team_id,
                case when g.home_team_abbrev = ? then g.away_team_abbrev else g.home_team_abbrev end as opponent,
                case when g.home_team_abbrev = ? then g.home_score    else g.away_score    end as gf,
                case when g.home_team_abbrev = ? then g.away_score    else g.home_score    end as ga,
                g.home_team_abbrev = ?                                                          as is_home
            from main.stg_games g
            where (g.home_team_abbrev = ? or g.away_team_abbrev = ?) and g.season = ?
        ),
        shot_stats as (
            select
                tg.game_id,
                round(sum(case when se.team_id  = tg.team_id and se.event_type != 'blocked-shot'
                               then coalesce(se.x_goal, 0) else 0 end), 2) as xg_for,
                round(sum(case when se.team_id != tg.team_id and se.event_type != 'blocked-shot'
                               then coalesce(se.x_goal, 0) else 0 end), 2) as xg_against
            from main.mart_shot_events se
            join team_games tg on tg.game_id = se.game_id
            where se.period < 5
            group by tg.game_id
        )
        select
            tg.game_id,
            row_number() over (order by tg.game_id) as game_num,
            tg.game_date,
            tg.opponent,
            tg.is_home,
            tg.gf,
            tg.ga,
            ss.xg_for,
            ss.xg_against,
            case
                when (tg.is_home and tg.home_win) or (not tg.is_home and not tg.home_win) then 'W'
                when tg.last_period_type != 'REG' then 'OTL'
                else 'L'
            end as result
        from team_games tg
        join shot_stats ss on ss.game_id = tg.game_id
        order by tg.game_id
    """, [team_abbrev] * 7 + [season]).df()
    conn.close()
    return df


@st.cache_data(ttl=3600)
def get_all_team_stats(season: int):
    conn = connect()
    df = conn.execute("""
        with all_teams as (
            select distinct
                home_team_abbrev as team_abbrev,
                home_team_id     as team_id
            from main.stg_games where season = ?
            union
            select distinct
                away_team_abbrev,
                away_team_id
            from main.stg_games where season = ?
        ),
        team_games as (
            select
                t.team_abbrev,
                t.team_id,
                g.game_id,
                g.home_win,
                g.last_period_type,
                g.home_team_abbrev = t.team_abbrev as is_home
            from main.stg_games g
            join all_teams t on t.team_id = g.home_team_id or t.team_id = g.away_team_id
            where g.season = ?
        ),
        shots_for as (
            select
                tg.team_abbrev,
                sum(case when se.event_type = 'goal'          then 1 else 0 end) as goals_for,
                sum(case when se.event_type != 'blocked-shot' then coalesce(se.x_goal, 0) else 0 end) as xg_for,
                count(*) as shots_for,
                count(distinct tg.game_id) as games_played,
                sum(case when se.event_type in ('shot-on-goal', 'goal') then 1 else 0 end) as sog_for
            from main.mart_shot_events se
            join team_games tg on tg.game_id = se.game_id and tg.team_id = se.team_id
            where se.period < 5
            group by tg.team_abbrev
        ),
        shots_against as (
            select
                tg.team_abbrev,
                sum(case when se.event_type = 'goal'          then 1 else 0 end) as goals_against,
                sum(case when se.event_type != 'blocked-shot' then coalesce(se.x_goal, 0) else 0 end) as xg_against,
                sum(case when se.event_type in ('shot-on-goal', 'goal') then 1 else 0 end) as sog_against
            from main.mart_shot_events se
            join team_games tg on tg.game_id = se.game_id and tg.team_id != se.team_id
            where se.period < 5
            group by tg.team_abbrev
        )
        select
            sf.team_abbrev,
            sf.games_played,
            round(sf.goals_for  * 1.0 / sf.games_played, 2) as gf_per_game,
            round(sa.goals_against * 1.0 / sf.games_played, 2) as ga_per_game,
            round(sf.xg_for     / sf.games_played, 3) as xg_for_per_game,
            round(sa.xg_against / sf.games_played, 3) as xg_against_per_game,
            round((sf.xg_for - sa.xg_against) / sf.games_played, 3) as xg_diff_per_game,
            round(sf.goals_for * 1.0 / nullif(sf.shots_for, 0) * 100, 1) as sh_pct,
            round(sf.goals_for * 1.0 / nullif(sf.sog_for, 0) * 100, 1)               as sh_pct_sog,
            round((1.0 - sa.goals_against * 1.0 / nullif(sa.sog_against, 0)) * 100, 1) as sv_pct
        from shots_for sf
        join shots_against sa on sa.team_abbrev = sf.team_abbrev
        order by xg_for_per_game desc
    """, [season, season, season]).df()
    conn.close()
    return df


@st.cache_data(ttl=3600)
def get_team_roster(team_abbrev: str, season: int):
    conn = connect()
    df = conn.execute("""
        select
            p.player_id,
            p.full_name,
            p.position,
            p.headshot_url,
            p.team_logo_url,
            m.games_played,
            m.goals,
            coalesce(m.assists, 0)      as assists,
            coalesce(m.points, 0)       as points,
            m.shots_on_goal,
            m.sh_pct,
            round(m.total_xg, 1)        as total_xg,
            round(m.xg_per_game, 3)     as xg_per_game,
            m.goals_above_expected      as gax
        from main.mart_player_shooting m
        join main.stg_players p on p.player_id = m.shooter_id
        where p.team_abbrev = ? and m.season = ?
        order by m.total_xg desc
    """, [team_abbrev, season]).df()
    conn.close()
    return df
