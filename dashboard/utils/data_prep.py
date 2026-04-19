import pandas as pd
import numpy as np


def prepare_filtered_shots(shots_df, game_log_df, strength_sel, period_sel, event_sel):
    
    filtered = shots_df[
        shots_df["strength"].isin(strength_sel) &
        shots_df["period"].isin(period_sel) &
        shots_df["event_type"].isin(event_sel)
    ].copy()

    mask = filtered["x_coord"] < 0
    filtered.loc[mask, "x_coord"] = -filtered.loc[mask, "x_coord"]
    filtered.loc[mask, "y_coord"] = -filtered.loc[mask, "y_coord"]

    filtered = filtered.merge(
        game_log_df[["game_id", "opponent", "is_home"]], on="game_id", how="left"
    )

    filtered["date_str"] = filtered["game_date"].dt.strftime("%b %d").fillna("—")
    opp = filtered["opponent"].fillna("—")
    prefix = np.where(filtered["is_home"], "vs ", "at ")
    filtered["opp_label"] = prefix + opp

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
            nongoals_df[nongoals_df["shot_type"] == selected_shot_type],
            blocked_df[blocked_df["shot_type"] == selected_shot_type],
        )
    return goals_df, nongoals_df, blocked_df

def prepare_shot_type_breakdown(filtered_shots):
    breakdown = (
        filtered_shots[filtered_shots["shot_type"].notna()]
        .groupby("shot_type")
        .agg(shots=("event_type", "count"), goals=("event_type", lambda x: (x == "goal").sum()))
        .reset_index()
        .assign(
            shots=lambda d: d["shots"].astype(int),
            goals=lambda d: d["goals"].astype(int),
            sh_pct=lambda d: (d["goals"].astype(float) / d["shots"].astype(float) * 100).round(1),
            volume_pct=lambda d: (d["shots"].astype(float) / d["shots"].sum() * 100).round(1),
        )
        .sort_values("shots", ascending=True)
    )
    return breakdown

def extract_clip_url(customdata):
    url = str(customdata[5]) if len(customdata) > 5 else ""
    is_invalid = url in ("", "nan", "None")

    if is_invalid and len(customdata) > 6:
        url = str(customdata[6])

    return "" if url in ("", "nan", "None") else url
