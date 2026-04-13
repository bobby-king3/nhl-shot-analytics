with source as (
    select * from {{ source('nhl', 'raw_moneypuck_shots') }}
),

final as (
    select
        -- identifiers
        game_id                                     as mp_game_id,
        cast(shooterPlayerId as integer)            as shooter_id,
        shooterName                                 as shooter_name,
        season                                      as mp_season,
        team                                        as team_location,
        period,
        time                                        as seconds_elapsed,
        xCordAdjusted                               as x_coord,
        yCordAdjusted                               as y_coord,
        shotType                                    as shot_type,
        event                                       as event_type,
        cast(shotRush as boolean)                   as is_rush,
        cast(shotRebound as boolean)                as is_rebound,
        cast(isPlayoffGame as boolean)              as is_playoff,
        xGoal                                       as x_goal

    from source
)

select * from final