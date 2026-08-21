{{
    config(
        materialized='table'
    )
}}

with team_map as (
    -- keyed on team_id: UTA covers two ids (59 Utah HC, 68 Mammoth)
    select distinct home_team_id as team_id, home_team_abbrev as team_abbrev
    from {{ ref('stg_games') }}

    union

    select distinct away_team_id as team_id, away_team_abbrev as team_abbrev
    from {{ ref('stg_games') }}
),

stints as (
    select
        s.shooter_id                                                     as player_id,
        s.season,
        s.team_id,
        t.team_abbrev,
        count(distinct s.game_id)                                        as games_played,
        count(*)                                                         as shot_attempts,
        count(*) filter (where s.event_type in ('shot-on-goal', 'goal')) as shots_on_goal,
        count(*) filter (where s.event_type = 'goal')                    as goals,
        round(sum(s.x_goal), 3)                                          as total_xg,
        round(
            count(*) filter (where s.event_type = 'goal') - sum(s.x_goal), 2
        )                                                                as goals_above_expected,
        round(
            100.0 * count(*) filter (where s.event_type = 'goal')
            / nullif(count(*) filter (where s.event_type in ('shot-on-goal', 'goal')), 0), 1
        )                                                                as sh_pct,
        min(s.game_date)                                                 as first_game_date,
        max(s.game_date)                                                 as last_game_date

    from {{ ref('mart_shot_events') }} s
    join team_map t on t.team_id = s.team_id
    where s.period < 5
    group by 1, 2, 3, 4
)

select
    *,
    'https://assets.nhle.com/logos/nhl/svg/' || team_abbrev || '_light.svg' as team_logo_url,
    count(*) over (partition by player_id, season)                          as team_count,
    row_number() over (
        partition by player_id, season
        order by shot_attempts desc, last_game_date desc
    ) = 1                                                                   as is_primary_team

from stints
