with stg as (
    select * from {{ ref('stg_play_by_play') }}
),

games as (
    select
        game_id,
        home_team_id,
        away_team_id
    from {{ ref('stg_games') }}
),

mp as (
    -- Deduplicate MoneyPuck: saw rare cases where same player shoots twice in same second
    select
        mp_game_id,
        shooter_id,
        period,
        seconds_elapsed,
        max(x_goal)     as x_goal,
        max(is_rush)    as is_rush,
        max(is_rebound) as is_rebound
    from {{ ref('stg_moneypuck_shots') }}
    group by 1, 2, 3, 4
),

parsed as (
    select
        *,
        cast(substr(situation_code, 1, 1) as integer) as away_goalie,
        cast(substr(situation_code, 2, 1) as integer) as away_skaters,
        cast(substr(situation_code, 3, 1) as integer) as home_skaters,
        cast(substr(situation_code, 4, 1) as integer) as home_goalie,
        (cast(split_part(time_in_period, ':', 1) as integer) * 60
            + cast(split_part(time_in_period, ':', 2) as integer)) as seconds_in_period

    from stg
    where x_coord is not null and y_coord is not null
),

joined as (
    select
        parsed.*,
        g.home_team_id,
        g.away_team_id,
        mp.x_goal,
        mp.is_rush,
        mp.is_rebound
    from parsed
    left join games g
        on g.game_id = parsed.game_id
    left join mp
        on cast(substring(cast(parsed.game_id as varchar), 5) as integer) = mp.mp_game_id
        and parsed.shooter_id = mp.shooter_id
        and parsed.period = mp.period
        and ((parsed.period - 1) * 1200) + parsed.seconds_in_period = mp.seconds_elapsed
),

-- Determine which net the shot is going to based on the shooter's team and side
with_net as (
    select
        joined.*,
        case
            when team_id = home_team_id and home_defending_side = 'left'  then  89.0
            when team_id = home_team_id and home_defending_side = 'right' then -89.0
            when team_id = away_team_id and home_defending_side = 'left'  then -89.0
            when team_id = away_team_id and home_defending_side = 'right' then  89.0
            -- fallback if home_defending_side is missing
            when x_coord >= 0 then 89.0
            else -89.0
        end as net_x
    from joined
),

final as (
    select
        game_id,
        event_id,
        season,
        period,
        time_in_period,
        seconds_in_period,
        event_type,
        x_coord,
        y_coord,
        shot_type,
        shooter_id,
        goalie_id,
        team_id,
        situation_code,
        away_skaters,
        home_skaters,
        away_goalie,
        home_goalie,
        home_defending_side,
        away_score,
        home_score,
        highlight_clip_url,
        raw,
        net_x,
        round(sqrt(power(x_coord - net_x, 2) + power(y_coord, 2)), 2) as shot_distance,
        round(degrees(atan2(abs(y_coord), abs(net_x - x_coord))), 2) as shot_angle,

        case
            when team_id = home_team_id and away_goalie = 0 then true
            when team_id = away_team_id and home_goalie = 0 then true
            else false
        end as is_empty_net,

        case
            when team_id = home_team_id and away_goalie = 0                       then 'EN'
            when team_id = away_team_id and home_goalie = 0                       then 'EN'
            when away_skaters = home_skaters and away_skaters = 5                 then '5v5'
            when away_skaters = home_skaters and away_skaters = 4                 then '4v4'
            when away_skaters = home_skaters and away_skaters = 3                 then '3v3'
            when away_skaters != home_skaters                                     then 'PP/SH'
            else 'other'
        end as strength,
        x_goal,
        is_rush,
        is_rebound

    from with_net
)

select * from final
