{{
    config(
        materialized='table'
    )
}}

with shots as (
    select * from {{ ref('mart_shot_events') }}
    where shooter_id is not null
    and period < 5
),

player_season as (
    select
        shooter_id,
        season,

        -- volume
        count(*)                                                                        as shot_attempts,
        count(*) filter (where event_type in ('shot-on-goal', 'goal'))                  as shots_on_goal,
        count(*) filter (where event_type = 'goal')                                     as goals,

        -- xG (only on shots where MoneyPuck has a value — excludes blocked shots)
        round(sum(x_goal) filter (where event_type != 'blocked-shot'), 3)              as total_xg,
        round(avg(x_goal) filter (where event_type != 'blocked-shot'), 4)              as avg_xg_per_shot,

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

        -- shooting percentage
        round(
            100.0 * count(*) filter (where event_type = 'goal')
            / nullif(count(*) filter (where event_type in ('shot-on-goal', 'goal')), 0), 1
        )                                                                               as sh_pct,

        -- goals above expected
        round(
            count(*) filter (where event_type = 'goal')
            - sum(x_goal) filter (where event_type != 'blocked-shot'), 2
        )                                                                               as goals_above_expected

    from shots
    group by 1, 2
),

with_player_stats as (
    select
        p.*,
        s.total_games_played as games_played,
        round(p.goals * 1.0 / nullif(s.total_games_played, 0), 3) as goals_per_game,
        round(p.total_xg / nullif(s.total_games_played, 0), 3) as xg_per_game,
        s.assists,
        s.points,
        s.plus_minus,
        s.pp_points,
        s.toi_per_game_min
    from player_season p
    left join {{ ref('stg_player_stats') }} s
        on  s.player_id = p.shooter_id
        and s.season    = p.season
),

-- only rank players with meaningful sample sizes
qualified as (
    select *
    from with_player_stats
    where shot_attempts >= 50
),

with_percentiles as (
    select
        *,

        -- percentile ranks (0-1 scale, higher = better)
        round(percent_rank() over (partition by season order by goals_per_game),        3)  as goals_per_game_pctile,
        round(percent_rank() over (partition by season order by sh_pct),               3)  as sh_pct_pctile,
        round(percent_rank() over (partition by season order by avg_xg_per_shot),      3)  as avg_xg_per_shot_pctile,
        round(percent_rank() over (partition by season order by xg_per_game),          3)  as xg_per_game_pctile,
        round(percent_rank() over (partition by season order by rebound_shot_pct),       3)  as rebound_shot_pct_pctile,
        round(percent_rank() over (partition by season order by avg_shot_distance desc), 3)  as shot_distance_pctile,
        round(percent_rank() over (partition by season order by goals_above_expected),   3)  as goals_above_expected_pctile

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
