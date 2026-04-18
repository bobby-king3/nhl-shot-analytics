with source as (
    select * from {{ source('nhl', 'raw_games') }}
)

select
    game_id,
    season,
    game_type,
    cast(game_date as date)                         as game_date,
    cast(start_time_utc as timestamp)               as start_time_utc,
    venue,
    home_team_id,
    home_team_abbrev,
    home_score,
    away_team_id,
    away_team_abbrev,
    away_score,
    last_period_type,
    case
        when last_period_type = 'REG' then 'Regulation'
        when last_period_type = 'OT'  then 'Overtime'
        when last_period_type = 'SO'  then 'Shootout'
    end                                             as game_outcome,
    home_score > away_score                         as home_win,
    ingested_at

from source
