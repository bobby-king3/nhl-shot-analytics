{{
    config(
        materialized='table'
    )
}}

with games as (
    -- excludes game types 19/20 (4 Nations), played by national teams
    select * from {{ ref('stg_games') }}
    where game_type in (2, 3)
),

-- one row per team per game, from that team's perspective
team_games as (
    select
        season,
        game_id,
        game_type,
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
        game_type,
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

team_shots as (
    select
        game_id,
        team_id,
        count(*) as shot_attempts,
        count(*) filter (where event_type in ('shot-on-goal', 'goal')) as sog,
        count(*) filter (where event_type != 'blocked-shot') as unblocked_attempts,
        count(x_goal) filter (where event_type != 'blocked-shot') as modeled_attempts,
        sum(x_goal) filter (where event_type != 'blocked-shot') as xg,
        count(*) filter (where is_5v5 and event_type = 'goal') as goals_5v5,
        count(*) filter (where is_5v5 and event_type in ('shot-on-goal', 'goal')) as sog_5v5,
        count(*) filter (where is_5v5 and event_type != 'blocked-shot') as unblocked_attempts_5v5,
        count(x_goal) filter (where is_5v5 and event_type != 'blocked-shot') as modeled_attempts_5v5,
        sum(x_goal) filter (where is_5v5 and event_type != 'blocked-shot') as xg_5v5
    from {{ ref('mart_shot_events') }}
    where period_type in ('REG', 'OT')
    group by 1, 2
),

game_shots as (
    select
        tg.*,
        coalesce(sf.shot_attempts, 0) as shot_attempts_for,
        coalesce(sa.shot_attempts, 0) as shot_attempts_against,
        coalesce(sf.sog, 0) as sog_for,
        coalesce(sa.sog, 0) as sog_against,
        coalesce(sf.unblocked_attempts, 0) as unblocked_attempts_for,
        coalesce(sa.unblocked_attempts, 0) as unblocked_attempts_against,
        coalesce(sf.modeled_attempts, 0) as modeled_attempts_for,
        coalesce(sa.modeled_attempts, 0) as modeled_attempts_against,
        sf.xg as measured_xg_for,
        sa.xg as measured_xg_against,
        coalesce(sf.goals_5v5, 0) as goals_for_5v5,
        coalesce(sa.goals_5v5, 0) as goals_against_5v5,
        coalesce(sf.sog_5v5, 0) as sog_for_5v5,
        coalesce(sf.unblocked_attempts_5v5, 0) as unblocked_attempts_for_5v5,
        coalesce(sa.unblocked_attempts_5v5, 0) as unblocked_attempts_against_5v5,
        coalesce(sf.modeled_attempts_5v5, 0) as modeled_attempts_for_5v5,
        coalesce(sa.modeled_attempts_5v5, 0) as modeled_attempts_against_5v5,
        sf.xg_5v5 as measured_xg_for_5v5,
        sa.xg_5v5 as measured_xg_against_5v5,

        -- Require some modeled data from each side that recorded unblocked attempts.
        modeled_attempts_for + modeled_attempts_against > 0
            and (unblocked_attempts_for = 0 or modeled_attempts_for > 0)
            and (unblocked_attempts_against = 0 or modeled_attempts_against > 0) as has_xg,
        modeled_attempts_for_5v5 + modeled_attempts_against_5v5 > 0
            and (unblocked_attempts_for_5v5 = 0 or modeled_attempts_for_5v5 > 0)
            and (unblocked_attempts_against_5v5 = 0 or modeled_attempts_against_5v5 > 0) as has_xg_5v5
    from team_games tg
    left join team_shots sf on sf.game_id = tg.game_id and sf.team_id = tg.team_id
    left join team_shots sa on sa.game_id = tg.game_id and sa.team_id = tg.opponent_id
)

select
    -- identifiers
    tg.season,
    tg.game_id,
    tg.game_type,
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
    -- Shootout winners get one extra marker in the final score, not counting this towards team GF/GA.
    tg.gf - case when tg.last_period_type = 'SO' and tg.won then 1 else 0 end as goals_for,
    tg.ga - case when tg.last_period_type = 'SO' and not tg.won then 1 else 0 end as goals_against,
    tg.won,
    tg.last_period_type,
    case
        when tg.won then 'W'
        when not tg.won and tg.last_period_type != 'REG' and tg.game_type = 2 then 'OTL'
        else 'L'
    end as result,

    tg.shot_attempts_for,
    tg.shot_attempts_against,
    tg.sog_for,
    tg.sog_against,
    tg.unblocked_attempts_for,
    tg.unblocked_attempts_against,
    tg.modeled_attempts_for,
    tg.modeled_attempts_against,
    case when tg.has_xg then coalesce(tg.measured_xg_for, 0) end as xg_for,
    case when tg.has_xg then coalesce(tg.measured_xg_against, 0) end as xg_against,

    tg.goals_for_5v5,
    tg.goals_against_5v5,
    tg.sog_for_5v5,
    tg.unblocked_attempts_for_5v5,
    tg.unblocked_attempts_against_5v5,
    tg.modeled_attempts_for_5v5,
    tg.modeled_attempts_against_5v5,
    case when tg.has_xg_5v5 then coalesce(tg.measured_xg_for_5v5, 0) end as xg_for_5v5,
    case when tg.has_xg_5v5 then coalesce(tg.measured_xg_against_5v5, 0) end as xg_against_5v5

from game_shots tg
