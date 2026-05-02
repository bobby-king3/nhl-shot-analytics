import numpy as np

def prepare_filtered_shots(shots_df, game_log_df, strength_sel, period_sel, event_sel):
    strength_opts = shots_df["strength"].dropna().unique()
    period_opts = shots_df["period"].dropna().unique()
    event_opts = shots_df["event_type"].dropna().unique()

    active_strength = strength_sel if strength_sel else strength_opts
    active_period = period_sel if period_sel else period_opts
    active_event = event_sel if event_sel else event_opts

    filtered = shots_df[
        shots_df["strength"].isin(active_strength) &
        shots_df["period"].isin(active_period) &
        shots_df["event_type"].isin(active_event)
    ].copy()

    mask = filtered["x_coord"] < 0
    filtered.loc[mask, "x_coord"] = -filtered.loc[mask, "x_coord"]
    filtered.loc[mask, "y_coord"] = -filtered.loc[mask, "y_coord"]

    filtered = filtered.merge(
        game_log_df[["game_id", "opponent", "is_home"]], on="game_id", how="left"
    )

    filtered["date_str"] = filtered["game_date"].dt.strftime("%b %d").fillna("—")
    prefix = np.where(filtered["is_home"], "vs ", "at ")
    filtered["opp_label"] = prefix + filtered["opponent"].fillna("—")

    return filtered

def split_shots_by_type(filtered_shots):
    goals = filtered_shots[filtered_shots["event_type"] == "goal"]
    blocked = filtered_shots[filtered_shots["event_type"] == "blocked-shot"]
    nongoals = filtered_shots[~filtered_shots["event_type"].isin(["goal", "blocked-shot"])]
    return goals, blocked, nongoals

def apply_shot_type_filter(goals_df, blocked_df, nongoals_df, selected_shot_type):
    if selected_shot_type:
        return (
            goals_df[goals_df["shot_type"] == selected_shot_type],
            blocked_df[blocked_df["shot_type"] == selected_shot_type],
            nongoals_df[nongoals_df["shot_type"] == selected_shot_type],
        )
    return goals_df, blocked_df, nongoals_df

def prepare_shot_type_breakdown(filtered_shots):
    breakdown = (
        filtered_shots[filtered_shots["shot_type"].notna()]
        .groupby("shot_type")
        .agg(shots=("event_type", "count"), goals=("event_type", lambda x: (x == "goal").sum()))
        .reset_index()
        .assign(
            sh_pct=lambda d: (d["goals"] / d["shots"] * 100).round(1),
            volume_pct=lambda d: (d["shots"] / d["shots"].sum() * 100).round(1),
        )
        .sort_values("shots", ascending=True)
    )
    return breakdown

def extract_clip_url(customdata):
    n = len(customdata)
    if n == 9:
        idx = 6   # non-goal (event_type, dist, angle, xg, strength, period, clip_url, date, opp)
    elif n == 8:
        idx = 5   # goal (dist, angle, xg, strength, period, clip_url, date, opp)
    else:
        return ""  # blocked shot (6 cols) or unknown = no clip URL
    url = str(customdata[idx])
    if url not in ("", "nan", "None"):
        return url
    return ""
