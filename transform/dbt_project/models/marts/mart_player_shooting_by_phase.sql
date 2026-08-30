{{
    config(
        materialized='table'
    )
}}

-- Runs alongside mart_player_shooting until the dashboard migrates off it.
-- No assists/points/TOI: /skater/summary is fetched without a gameTypeId,
-- so those totals combine both phases and can't be split here.

with shots as (
    select * from {{ ref('mart_shot_events') }}
    where shooter_id is not null
      -- period 5 in a playoff game is 2OT, not a shootout
      and not (game_type = 2 and period = 5)
),

player_phase as (
    select
        shooter_id,
        season,
        game_type,

        -- volume
        count(distinct game_id)                                                         as games_played,
        count(*)                                                                        as shot_attempts,
        count(*) filter (where event_type in ('shot-on-goal', 'goal'))                  as shots_on_goal,
        count(*) filter (where event_type = 'goal')                                     as goals,

        -- xG (only on shots where MoneyPuck has a value — excludes blocked shots)
        round(sum(x_goal), 3)                                                           as total_xg,
        round(avg(x_goal), 4)                                                           as avg_xg_per_shot,

        -- shot quality
        round(avg(shot_distance), 1)                                                    as avg_shot_distance,
        round(avg(shot_angle), 1)                                                       as avg_shot_angle,
        round(
            100.0 * count(*) filter (where is_rebound = true)
            / nullif(count(*), 0), 1
        )                                                                               as rebound_shot_pct,

        -- per_game rates
        round(
            count(*) filter (where event_type = 'goal')
            * 1.0 / nullif(count(distinct game_id), 0), 3
        )                                                                               as goals_per_game,
        round(
            sum(x_goal)
            / nullif(count(distinct game_id), 0), 3
        )                                                                               as xg_per_game,

        -- shooting percentage
        round(
            100.0 * count(*) filter (where event_type = 'goal')
            / nullif(count(*) filter (where event_type in ('shot-on-goal', 'goal')), 0), 1
        )                                                                               as sh_pct,

        -- goals above expected
        round(
            count(*) filter (where event_type = 'goal') - sum(x_goal), 2
        )                                                                               as goals_above_expected

    from shots
    group by 1, 2, 3
),

-- a playoff run is 4-22 games, so 50 attempts would qualify only a fifth of the pool
qualified as (
    select *
    from player_phase
    where shot_attempts >= case when game_type = 2 then 50 else 20 end
),

with_percentiles as (
    select
        *,

        count(*) over (partition by season, game_type)                                      as phase_pool_size,

        -- percentile ranks (0-1 scale, higher = better), within phase
        round(percent_rank() over (partition by season, game_type order by goals_per_game),        3) as goals_per_game_pctile,
        round(percent_rank() over (partition by season, game_type order by sh_pct),                3) as sh_pct_pctile,
        round(percent_rank() over (partition by season, game_type order by avg_xg_per_shot),       3) as avg_xg_per_shot_pctile,
        round(percent_rank() over (partition by season, game_type order by xg_per_game),           3) as xg_per_game_pctile,
        round(percent_rank() over (partition by season, game_type order by rebound_shot_pct),      3) as rebound_shot_pct_pctile,
        round(percent_rank() over (partition by season, game_type order by avg_shot_distance desc),3) as shot_distance_pctile,
        round(percent_rank() over (partition by season, game_type order by goals_above_expected),  3) as goals_above_expected_pctile

    from qualified
),

season_teams as (
    select
        player_id,
        season,
        max(team_abbrev)   filter (where is_primary_team) as primary_team_abbrev,
        max(team_logo_url) filter (where is_primary_team) as primary_team_logo_url
    from {{ ref('mart_player_team_season') }}
    group by 1, 2
),

final as (
    select
        p.*,
        t.primary_team_abbrev,
        t.primary_team_logo_url
    from with_percentiles p
    left join season_teams t
        on  t.player_id = p.shooter_id
        and t.season    = p.season
)

select * from final
