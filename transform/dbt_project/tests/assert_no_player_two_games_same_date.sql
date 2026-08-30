-- game_date was once the UTC date, which collapsed back-to-backs onto one day
select
    shooter_id,
    game_date,
    count(distinct game_id) as games
from {{ ref('mart_shot_events') }}
group by 1, 2
having count(distinct game_id) > 1
