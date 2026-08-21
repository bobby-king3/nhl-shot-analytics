{{
    config(
        materialized='table'
    )
}}

select
    -- identifiers
    player_id,

    -- name
    first_name,
    last_name,
    full_name,

    -- position / handedness
    position,
    shoots_catches,

    -- contract today; for a played season use mart_player_team_season
    team_id       as current_team_id,
    team_abbrev   as current_team_abbrev,
    team_logo_url as current_team_logo_url,

    -- bio
    sweater_number,
    height_in,
    weight_lbs,
    birth_date,
    birth_city,
    birth_country,

    -- presentation
    headshot_url,

    -- status
    is_active

from {{ ref('stg_players') }}