{{
    config(
        materialized='table'
    )
}}

-- otl, points and so_wins are regular season concepts and are null for playoffs

with team_games as (
    select * from {{ ref('mart_team_games') }}
)

select
    -- identifiers
    season,
    team_abbrev,
    team_id,
    game_type,

    -- record
    count(*)                                                                       as games_played,
    count(*) filter (where result = 'W')                                           as wins,
    count(*) filter (where result = 'L')                                           as losses,
    case when game_type = 2 then count(*) filter (where result = 'OTL') end        as otl,
    case when game_type = 2 then 2 * count(*) filter (where result = 'W')
                               + count(*) filter (where result = 'OTL') end        as points,
    case when game_type = 2 then count(*) filter (
             where result = 'W' and last_period_type = 'SO') end                   as so_wins,

    -- totals
    sum(gf)                                                                        as goals_for,
    round(sum(xg_for), 1)                                                          as xg_for,
    sum(shot_attempts_for)                                                         as shot_attempts_for,
    sum(sog_for)                                                                   as sog_for,
    sum(ga)                                                                        as goals_against,
    round(sum(xg_against), 1)                                                      as xg_against,
    sum(shot_attempts_against)                                                     as shot_attempts_against,
    sum(sog_against)                                                               as sog_against,

    -- per-game rates
    round(sum(gf)     * 1.0 / count(*), 2)                                         as gf_per_game,
    round(sum(ga)     * 1.0 / count(*), 2)                                         as ga_per_game,
    round(sum(xg_for)           / count(*), 3)                                     as xg_for_per_game,
    round(sum(xg_against)       / count(*), 3)                                     as xg_against_per_game,
    round((sum(xg_for) - sum(xg_against)) / count(*), 3)                           as xg_diff_per_game,
    round(sum(xg_for) - sum(xg_against), 1)                                        as xg_differential,

    -- shooting / save percentages
    round(sum(gf) * 100.0 / nullif(sum(shot_attempts_for), 0), 1)              as sh_pct,
    round(sum(gf) * 100.0 / nullif(sum(sog_for), 0),           1)              as sh_pct_sog,
    round((1.0 - sum(ga) * 1.0 / nullif(sum(sog_against), 0)) * 100, 1)        as sv_pct

from team_games
group by season, team_abbrev, team_id, game_type
