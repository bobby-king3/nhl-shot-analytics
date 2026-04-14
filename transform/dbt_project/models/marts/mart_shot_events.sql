{{
    config(
        materialized='incremental',
        unique_key='event_id_pk'
    )
}}

with shots as (
    select * from {{ ref('int_shot_events') }}
    {% if is_incremental() %}
        where game_id not in (select distinct game_id from {{ this }})
    {% endif %}
)

select
    -- primary key
    {{ dbt_utils.generate_surrogate_key(['game_id', 'event_id']) }} as event_id_pk,

    -- identifiers
    game_id,
    event_id,
    season,
    shooter_id,
    goalie_id,
    team_id,

    -- game context
    period,
    time_in_period,
    seconds_in_period,
    away_score,
    home_score,
    strength,
    home_defending_side,

    -- shot details
    event_type,
    shot_type,
    x_coord,
    y_coord,
    shot_distance,
    shot_angle,
    is_empty_net,

    -- moneypuck xG and shot context
    x_goal,
    is_rush,
    is_rebound,

    -- video
    highlight_clip_url

from shots
