with source as (
    select * from {{ source('nhl', 'raw_play_by_play') }}
)

select
    game_id,
    event_id,
    season,
    period,
    time_in_period,
    event_type,
    x_coord,
    y_coord,
    shot_type,
    shooter_id,
    goalie_id,
    team_id,
    situation_code,
    home_defending_side,
    away_score,
    home_score,
    highlight_clip_url,
    raw
from source
