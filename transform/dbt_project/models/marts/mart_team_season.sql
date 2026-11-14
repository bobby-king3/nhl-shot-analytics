{{
    config(
        materialized='table'
    )
}}

-- Regular season only for team page headers

with team_games as (
    select * from {{ ref('mart_team_games') }}
    where game_type = 2
)

select
    -- identifiers
    season,
    team_abbrev,
    team_id,

    -- record
    count(*)                                                                       as games_played,
    count(*) filter (where result = 'W')                                           as wins,
    count(*) filter (where result = 'L')                                           as losses,
    count(*) filter (where result = 'OTL')                                         as otl,
    2 * count(*) filter (where result = 'W')
      + count(*) filter (where result = 'OTL')                                     as points,

    -- totals
    sum(goals_for)                                                                 as goals_for,
    sum(xg_for)                                                                     as xg_for,
    sum(shot_attempts_for)                                                         as shot_attempts_for,
    sum(sog_for)                                                                   as sog_for,
    sum(goals_against)                                                             as goals_against,
    sum(xg_against)                                                                 as xg_against,
    sum(shot_attempts_against)                                                     as shot_attempts_against,
    sum(sog_against)                                                               as sog_against,
    sum(unblocked_attempts_for)                                                    as unblocked_attempts_for,
    sum(unblocked_attempts_against)                                                as unblocked_attempts_against,
    sum(modeled_attempts_for)                                                      as modeled_attempts_for,
    sum(modeled_attempts_against)                                                  as modeled_attempts_against,
    count(xg_for)                                                                  as games_with_xg,
    sum(goals_for_5v5)                                                             as goals_for_5v5,
    sum(goals_against_5v5)                                                         as goals_against_5v5,
    sum(sog_for_5v5)                                                               as sog_for_5v5,
    sum(unblocked_attempts_for_5v5)                                                as unblocked_attempts_for_5v5,
    sum(unblocked_attempts_against_5v5)                                            as unblocked_attempts_against_5v5,
    sum(modeled_attempts_for_5v5)                                                  as modeled_attempts_for_5v5,
    sum(modeled_attempts_against_5v5)                                              as modeled_attempts_against_5v5,
    count(xg_for_5v5)                                                              as games_with_xg_5v5,
    sum(xg_for_5v5)                                                                as xg_for_5v5,
    sum(xg_against_5v5)                                                            as xg_against_5v5,

    -- per-game rates
    round(sum(goals_for)     * 1.0 / count(*), 2)                                   as gf_per_game,
    round(sum(goals_against) * 1.0 / count(*), 2)                                   as ga_per_game,
    round(sum(xg_for) / nullif(count(xg_for), 0), 3)                                 as xg_for_per_game,
    round(sum(xg_against) / nullif(count(xg_against), 0), 3)                         as xg_against_per_game,
    round((sum(xg_for) - sum(xg_against)) / nullif(count(xg_for), 0), 3)              as xg_diff_per_game,
    round(sum(xg_for) - sum(xg_against), 1)                                        as xg_differential,

    -- shooting / save percentages
    -- sh_pct_sog = goals / shots-on-goal
    -- sh_pct = goals / all shot attempts (includes missed and blocked)
    round(sum(goals_for) * 100.0 / nullif(sum(shot_attempts_for), 0), 1)        as sh_pct,
    round(sum(goals_for) * 100.0 / nullif(sum(sog_for), 0), 1)                  as sh_pct_sog,
    round((1.0 - sum(goals_against) * 1.0 / nullif(sum(sog_against), 0)) * 100, 1) as sv_pct

from team_games
group by season, team_abbrev, team_id
