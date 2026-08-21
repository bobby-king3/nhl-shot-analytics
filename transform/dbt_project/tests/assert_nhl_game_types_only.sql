select
    g.game_type,
    count(*) as shots
from {{ ref('mart_shot_events') }} s
join {{ ref('stg_games') }} g on g.game_id = s.game_id
where g.game_type not in (2, 3)
group by 1
