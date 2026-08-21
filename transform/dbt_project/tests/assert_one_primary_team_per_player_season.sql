select
    player_id,
    season
from {{ ref('mart_player_team_season') }}
group by 1, 2
having count(*) filter (where is_primary_team) <> 1
