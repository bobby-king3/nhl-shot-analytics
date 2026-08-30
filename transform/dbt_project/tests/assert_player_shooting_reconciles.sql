with expected_season as (
    select
        shooter_id,
        season,
        count(*)                                    as shot_attempts,
        count(*) filter (where event_type = 'goal') as goals
    from {{ ref('mart_shot_events') }}
    where shooter_id is not null
      and not (game_type = 2 and period = 5)
    group by 1, 2
),

expected_phase as (
    select
        shooter_id,
        season,
        game_type,
        count(*)                                    as shot_attempts,
        count(*) filter (where event_type = 'goal') as goals
    from {{ ref('mart_shot_events') }}
    where shooter_id is not null
      and not (game_type = 2 and period = 5)
    group by 1, 2, 3
)

select
    'mart_player_shooting' as model,
    m.shooter_id,
    m.season
from {{ ref('mart_player_shooting') }} m
join expected_season e
  on  e.shooter_id = m.shooter_id
  and e.season     = m.season
where m.shot_attempts <> e.shot_attempts
   or m.goals         <> e.goals

union all

select
    'mart_player_shooting_by_phase',
    m.shooter_id,
    m.season
from {{ ref('mart_player_shooting_by_phase') }} m
join expected_phase e
  on  e.shooter_id = m.shooter_id
  and e.season     = m.season
  and e.game_type  = m.game_type
where m.shot_attempts <> e.shot_attempts
   or m.goals         <> e.goals
