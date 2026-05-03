# NHL Shot Analytics

This project ingests NHL play-by-play, roster, schedule, and player data from the NHL API and leverages MoneyPuck shot data with modeled xG metrics per shot on goal.

## Pipeline

```
NHL API -> Python Extract -> DuckDB / MotherDuck -> dbt Transform -> Streamlit Dashboard
MoneyPuck shot files -> dbt Transform
```

## Background

The pipeline runs daily at 07:00 UTC with GitHub Actions. Each run pulls newly finished NHL games, play-by-play shot events, rosters, and skater stats from the public [NHL API](https://api-web.nhle.com/).

MoneyPuck is a hockey analytics site that publishes shot level data and models expected goals. This project uses MoneyPuck's public shot files for xG, rush shot, and rebound shot fields.

The production warehouse is hosted in MotherDuck. The Streamlit dashboard reads from dbt mart tables and is deployed as a cloud app.

## Dataset

355,344 MoneyPuck shot attempts across the 2023-24, 2024-25, and 2025-26 NHL seasons. The modeled data includes game context, shooter and goalie ids, team, period, time, shot type, rink coordinates, shot distance, shot angle, strength state, rush/rebound flags, expected goals, and highlight video links when available.

| Season | Shot attempts | Games | Shooters |
| --- | ---: | ---: | ---: |
| 2023-24 | 122,472 | 1,400 | 909 |
| 2024-25 | 119,870 | 1,398 | 917 |
| 2025-26 | 113,002 | 1,323 | 939 |

## dbt Models

**Staging**
- `stg_games` - cleaned NHL schedule and game result data
- `stg_play_by_play` - typed shot level play by play events from the NHL API
- `stg_moneypuck_shots` - MoneyPuck public shot data renamed to NHL conventions
- `stg_players` - roster data with player names, positions, headshots, and team logos
- `stg_player_stats` - season level skater stats

**Intermediate**
- `int_shot_events` - joins NHL play by play to MoneyPuck shot data, parses strength state, and calculates shot distance and angles

**Marts**
- `mart_shot_events` - one row per shot event with game context, shot metrics, xG, and video links
- `mart_player_shooting` - one row per player season with goals, shots, xG, shooting rates, and league percentile ranks
- `mart_players` - player dimension table with bio and roster details
- `mart_team_games` - one row per team per game from each team's perspective
- `mart_team_season` - team season totals for record, goals, xG, shooting percentage, and save percentage

**Tests**
- `not_null`, `unique`, and `accepted_values` on key columns
- `dbt_utils.unique_combination_of_columns` on composite keys
- Range checks for xG values, percentile fields, period values, shooting percentage, and team records

## dbt Lineage

![dbt lineage graph](dbt_lineage.png)

## Dashboard

[Live Dashboard](https://nhl-shot-analytics.streamlit.app/)

Select any team to view season record, goals for and against, xG for and against, rolling xG share, shooting percentage, save percentage, recent games, and roster details.

Select any player to view a player card with season stats, league percentile rankings, shot type breakdown, game log, career season table, and a rink based shot map. Goal events can be clicked to watch the available goal video.

## Data Sources

- [NHL API](https://api-web.nhle.com/) - schedule, play by play, rosters, player stats, team logos, and highlight links
- [MoneyPuck](https://moneypuck.com/data.htm) - public shot data with pre-computed expected goals, rush shot, and rebound shot fields

## Future Work

- Build an expected goals model directly in the pipeline.
- Add a goalie analytics page with save percentage by zone and high-danger save rate.
