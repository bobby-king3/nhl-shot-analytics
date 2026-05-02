with source as (
    select * from {{ source('nhl', 'raw_players') }}
)

select
    player_id,
    first_name,
    last_name,
    first_name || ' ' || last_name as full_name,
    position,
    headshot_url,
    team_id,
    team_abbrev,
    case
        when team_abbrev is not null
        then 'https://assets.nhle.com/logos/nhl/svg/' || team_abbrev || '_light.svg'
    end as team_logo_url,
    is_active,
    sweater_number,
    height_in,
    weight_lbs,
    TRY_CAST(birth_date AS DATE) as birth_date,
    birth_city,
    birth_country,
    shoots_catches,
    ingested_at

from source
