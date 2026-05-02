{{
    config(
        materialized='table'
    )
}}

with games as (
    select * from {{ ref('stg_games') }}
),

shots as (
    select * from {{ ref('mart_shot_events') }}
    where period < 5
),

team_games as (
    select
        season,
        game_id,
        home_team_abbrev as team_abbrev,
        home_team_id     as team_id,
        true             as is_home,
        last_period_type,
        home_win         as won
    from games

    union all

    select
        season,
        game_id,
        away_team_abbrev,
        away_team_id,
        false,
        last_period_type,
        not home_win
    from games
),

team_record as (
    select
        season,
        team_abbrev,
        team_id,
        count(*)                                                                            as games_played,
        count(*) filter (where won)                                                         as wins,
        count(*) filter (where not won and last_period_type  = 'REG')                       as losses,
        count(*) filter (where not won and last_period_type != 'REG')                       as otl,
        2 * count(*) filter (where won)
          + count(*) filter (where not won and last_period_type != 'REG')                   as points
    from team_games
    group by 1, 2, 3
),

shots_for as (
    select
        tg.season,
        tg.team_abbrev,
        count(*) filter (where s.event_type = 'goal')                                       as goals_for,
        round(sum(coalesce(s.x_goal, 0)) filter (where s.event_type != 'blocked-shot'), 3)  as xg_for,
        count(*)                                                                            as shot_attempts_for,
        count(*) filter (where s.event_type in ('shot-on-goal', 'goal'))                    as sog_for
    from team_games tg
    join shots s
      on  s.game_id = tg.game_id
      and s.team_id = tg.team_id
    group by 1, 2
),

shots_against as (
    select
        tg.season,
        tg.team_abbrev,
        count(*) filter (where s.event_type = 'goal')                                       as goals_against,
        round(sum(coalesce(s.x_goal, 0)) filter (where s.event_type != 'blocked-shot'), 3)  as xg_against,
        count(*)                                                                            as shot_attempts_against,
        count(*) filter (where s.event_type in ('shot-on-goal', 'goal'))                    as sog_against
    from team_games tg
    join shots s
      on  s.game_id  = tg.game_id
      and s.team_id != tg.team_id
    group by 1, 2
)

select
    -- identifiers
    r.season,
    r.team_abbrev,
    r.team_id,

    -- record
    r.games_played,
    r.wins,
    r.losses,
    r.otl,
    r.points,

    -- totals
    sf.goals_for,
    round(sf.xg_for, 1)                                                                     as xg_for,
    sf.shot_attempts_for,
    sf.sog_for,
    sa.goals_against,
    round(sa.xg_against, 1)                                                                 as xg_against,
    sa.shot_attempts_against,
    sa.sog_against,

    -- per-game rates
    round(sf.goals_for      * 1.0 / r.games_played, 2)                                      as gf_per_game,
    round(sa.goals_against  * 1.0 / r.games_played, 2)                                      as ga_per_game,
    round(sf.xg_for / r.games_played, 3)                                                    as xg_for_per_game,
    round(sa.xg_against / r.games_played, 3)                                                as xg_against_per_game,
    round((sf.xg_for - sa.xg_against) / r.games_played, 3)                                  as xg_diff_per_game,
    round(sf.xg_for - sa.xg_against, 1)                                                     as xg_differential,

    -- shooting / save percentages
    -- sh_pct_sog = goals / shots-on-goal
    -- sh_pct = goals / all shot attempts (includes missed and blocked) 
    round(sf.goals_for       * 100.0 / nullif(sf.shot_attempts_for, 0), 1)                  as sh_pct,
    round(sf.goals_for       * 100.0 / nullif(sf.sog_for, 0),           1)                  as sh_pct_sog,
    round((1.0 - sa.goals_against * 1.0 / nullif(sa.sog_against, 0)) * 100, 1)              as sv_pct

from team_record r
left join shots_for     sf on sf.season = r.season and sf.team_abbrev = r.team_abbrev
left join shots_against sa on sa.season = r.season and sa.team_abbrev = r.team_abbrev
