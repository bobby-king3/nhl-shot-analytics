{{
    config(
        materialized='table'
    )
}}

with shots as (
    select * from {{ ref('int_shot_events') }}
),

games as (
    select game_id, game_date from {{ ref('stg_games') }}
)

select
    -- primary key
    {{ dbt_utils.generate_surrogate_key(['s.game_id', 's.event_id']) }} as event_id_pk,

    -- identifiers
    s.game_id,
    s.event_id,
    s.season,
    s.shooter_id,
    s.goalie_id,
    s.team_id,

    -- game context
    g.game_date,
    s.period,
    s.time_in_period,
    s.seconds_in_period,
    s.away_score,
    s.home_score,
    s.strength,
    s.home_defending_side,

    -- shot details
    s.event_type,
    s.shot_type,
    s.x_coord,
    s.y_coord,
    s.net_x,
    s.shot_distance,
    s.shot_angle,
    s.is_empty_net,

    -- moneypuck xG and shot context
    s.x_goal,
    s.is_rush,
    s.is_rebound,

    -- video
    s.highlight_clip_url

from shots s
left join games g on g.game_id = s.game_id
