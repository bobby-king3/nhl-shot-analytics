with source as (
    select * from {{ source('nhl', 'raw_player_stats') }}
)

select
    player_id,
    season_id as season,
    team_abbrev,
    position,
    games_played,
    playoff_games_played,
    games_played + playoff_games_played as total_games_played,
    playoff_assists,
    playoff_points,
    goals,
    assists,
    points,
    assists + playoff_assists as total_assists,
    points + playoff_points as total_points,
    plus_minus,
    pp_goals,
    pp_points,
    sh_goals,
    sh_points,
    shots,
    round(shooting_pct * 100, 1) as shooting_pct,
    round(toi_per_game / 60.0, 2) as toi_per_game_min
from source
