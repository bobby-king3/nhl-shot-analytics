-- int_shot_events inner joins stg_games, so a game present in play-by-play but
-- missing from raw_games would have its shots dropped rather than flagged.

select distinct p.game_id
from {{ ref('stg_play_by_play') }} p
left join {{ ref('stg_games') }} g on g.game_id = p.game_id
where g.game_id is null
