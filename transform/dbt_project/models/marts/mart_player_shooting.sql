{{
    config(
        materialized='table'
    )
}}

with shots as (
    select * from {{ ref('mart_shot_events') }}
    where shooter_id is not null
),

player_season as (
    select
        shooter_id,
        season,

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
            100.0 * count(*) filter (where is_rush = true)
            / nullif(count(*), 0), 1
        )                                                                               as rush_shot_pct,
        round(
            100.0 * count(*) filter (where is_rebound = true)
            / nullif(count(*), 0), 1
        )                                                                               as rebound_shot_pct,

        -- rates (per game, since we have no TOI)
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
        )                                                                               as sh_pct

    from shots
    group by 1, 2
),

-- only rank players with meaningful sample sizes
qualified as (
    select *
    from player_season
    where shot_attempts >= 50
),

with_percentiles as (
    select
        *,

        -- percentile ranks (0-1 scale, higher = better)
        round(percent_rank() over (partition by season order by goals_per_game),   3)  as goals_per_game_pctile,
        round(percent_rank() over (partition by season order by sh_pct),           3)  as sh_pct_pctile,
        round(percent_rank() over (partition by season order by avg_xg_per_shot),  3)  as avg_xg_per_shot_pctile,
        round(percent_rank() over (partition by season order by xg_per_game),      3)  as xg_per_game_pctile,
        round(percent_rank() over (partition by season order by rush_shot_pct),    3)  as rush_shot_pct_pctile,
        -- lower distance = better (driving to the net)
        round(percent_rank() over (partition by season order by avg_shot_distance desc), 3) as shot_distance_pctile

    from qualified
)

select * from with_percentiles
