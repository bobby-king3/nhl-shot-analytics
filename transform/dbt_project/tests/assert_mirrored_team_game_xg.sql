with team_games as (
    select * from {{ ref('mart_team_games') }}
)

select team.game_id, team.team_id
from team_games team
left join team_games opponent
    on opponent.game_id = team.game_id and opponent.team_id = team.opponent_id
where opponent.team_id is null
    or team.xg_for is distinct from opponent.xg_against
    or team.xg_for_5v5 is distinct from opponent.xg_against_5v5
    or team.unblocked_attempts_for is distinct from opponent.unblocked_attempts_against
    or team.unblocked_attempts_for_5v5 is distinct from opponent.unblocked_attempts_against_5v5
    or team.modeled_attempts_for is distinct from opponent.modeled_attempts_against
    or team.modeled_attempts_for_5v5 is distinct from opponent.modeled_attempts_against_5v5
    or team.goals_for_5v5 is distinct from opponent.goals_against_5v5
