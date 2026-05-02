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

-- one row per team per game, from that team's perspective
team_games as (
    select
        season,
        game_id,
        game_date,
        last_period_type,
        home_team_abbrev as team_abbrev,
        home_team_id     as team_id,
        away_team_abbrev as opponent_abbrev,
        away_team_id     as opponent_id,
        true             as is_home,
        home_score       as gf,
        away_score       as ga,
        home_win         as won
    from games

    union all

    select
        season,
        game_id,
        game_date,
        last_period_type,
        away_team_abbrev,
        away_team_id,
        home_team_abbrev,
        home_team_id,
        false,
        away_score,
        home_score,
        not home_win
    from games
),

shot_stats as (
    select
        tg.game_id,
        tg.team_id,
        count(*) filter (where s.team_id  = tg.team_id)                                                                              as shot_attempts_for,
        count(*) filter (where s.team_id  = tg.team_id and s.event_type in ('shot-on-goal', 'goal'))                                 as sog_for,
        round(sum(coalesce(s.x_goal, 0)) filter (where s.team_id  = tg.team_id and s.event_type != 'blocked-shot'), 3)               as xg_for,
        count(*) filter (where s.team_id != tg.team_id)                                                                              as shot_attempts_against,
        count(*) filter (where s.team_id != tg.team_id and s.event_type in ('shot-on-goal', 'goal'))                                 as sog_against,
        round(sum(coalesce(s.x_goal, 0)) filter (where s.team_id != tg.team_id and s.event_type != 'blocked-shot'), 3)               as xg_against
    from team_games tg
    left join shots s on s.game_id = tg.game_id
    group by 1, 2
)

select
    -- identifiers
    tg.season,
    tg.game_id,
    tg.game_date,

    -- team perspective
    tg.team_abbrev,
    tg.team_id,
    tg.is_home,
    tg.opponent_abbrev,
    tg.opponent_id,

    -- score / result
    tg.gf,
    tg.ga,
    tg.won,
    tg.last_period_type,
    case
        when tg.won                                       then 'W'
        when not tg.won and tg.last_period_type != 'REG'  then 'OTL'
        else 'L'
    end as result,

    -- shot stats (period < 5)
    coalesce(ss.shot_attempts_for, 0) as shot_attempts_for,
    coalesce(ss.sog_for, 0) as sog_for,
    coalesce(ss.xg_for, 0) as xg_for,
    coalesce(ss.shot_attempts_against, 0) as shot_attempts_against,
    coalesce(ss.sog_against, 0) as sog_against,
    coalesce(ss.xg_against, 0) as xg_against

from team_games tg
left join shot_stats ss
  on  ss.game_id = tg.game_id
  and ss.team_id = tg.team_id
