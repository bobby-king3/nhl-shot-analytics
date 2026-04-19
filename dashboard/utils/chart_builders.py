import plotly.graph_objects as go
import numpy as np
import pandas as pd

from dashboard.components.rink import make_rink_figure
from dashboard.utils.plotly_config import get_dark_layout, get_dark_xaxes, get_dark_yaxes, generate_bar_colors_for_selection
from dashboard.utils.styling import get_performance_color


def build_game_log_chart(
    game_log_df: pd.DataFrame,
    selected_game_ids: set,
    game_filter_active: bool,
    r: int,
    g: int,
    b: int,
    primary: str,
) -> go.Figure:
    rolling_avg = game_log_df["xg"].rolling(5, min_periods=1).mean()
    goal_games = game_log_df[game_log_df["goals"] > 0]

    bar_colors = generate_bar_colors_for_selection(
        game_log_df["game_id"],
        r, g, b,
        selected_value=None,
        selected_active=game_filter_active,
    )

    fig = go.Figure()

    # xG bars
    fig.add_trace(go.Bar(
        x=game_log_df["game_num"],
        y=game_log_df["xg"],
        marker=dict(color=bar_colors, line=dict(width=0)),
        hovertemplate="Game %{x} vs %{customdata}<br>xG: %{y:.3f}<extra></extra>",
        customdata=game_log_df["opponent"],
        showlegend=False,
    ))

    # 5-game rolling average
    fig.add_trace(go.Scatter(
        x=game_log_df["game_num"],
        y=rolling_avg,
        mode="lines",
        line=dict(color="rgba(255,255,255,0.5)", width=2, dash="dot"),
        hovertemplate="Game %{x}<br>5-game avg: %{y:.3f}<extra></extra>",
        showlegend=False,
    ))

    # Goal markers
    if len(goal_games) > 0:
        fig.add_trace(go.Scatter(
            x=goal_games["game_num"],
            y=goal_games["xg"],
            mode="markers",
            marker=dict(symbol="star", color=primary, size=14, line=dict(color="white", width=1.5)),
            hovertemplate="Game %{x}<br>GOAL — xG: %{y:.3f}<extra></extra>",
            showlegend=False,
        ))

    # Filter highlight rectangles
    if game_filter_active:
        selected_nums = game_log_df[game_log_df["game_id"].isin(selected_game_ids)]["game_num"].tolist()
        for gnum in selected_nums:
            fig.add_vrect(
                x0=gnum - 0.5, x1=gnum + 0.5,
                fillcolor=f"rgba({r},{g},{b},0.15)",
                line=dict(width=0),
                layer="below",
            )

    fig.update_xaxes(**get_dark_xaxes(title="Game"))
    fig.update_yaxes(**get_dark_yaxes(title="xG"))

    layout = get_dark_layout(height=220, margin_l=40, margin_r=20, margin_t=10, margin_b=30)
    layout["bargap"] = 0.15
    fig.update_layout(**layout)

    return fig


def build_shot_map(
    map_nongoals_df: pd.DataFrame,
    map_blocked_df: pd.DataFrame,
    map_goals_df: pd.DataFrame,
    primary: str,
) -> go.Figure:
    fig = make_rink_figure(height=520)
    xg_vals = map_nongoals_df["x_goal"].fillna(0).clip(0, 0.5)

    # Non-goals
    if len(map_nongoals_df) > 0:
        fig.add_trace(go.Scatter(
            x=map_nongoals_df["x_coord"],
            y=map_nongoals_df["y_coord"],
            mode="markers",
            marker=dict(
                color=xg_vals,
                colorscale="RdBu_r",
                cmin=0, cmax=0.5,
                size=8,
                opacity=0.75,
                colorbar=dict(
                    title=dict(text="xG", font=dict(color="white", size=11)),
                    tickfont=dict(color="white", size=9),
                    thickness=12, len=0.6, x=1.01,
                ),
                line=dict(width=0),
            ),
            customdata=np.column_stack([
                map_nongoals_df["event_type"],
                map_nongoals_df["shot_distance"].round(1),
                map_nongoals_df["shot_angle"].round(1),
                map_nongoals_df["x_goal"].round(3),
                map_nongoals_df["strength"],
                map_nongoals_df["period"],
                map_nongoals_df["highlight_clip_url"].fillna(""),
                map_nongoals_df["date_str"],
                map_nongoals_df["opp_label"],
            ]),
            hovertemplate=(
                "<b>%{customdata[0]}</b><br>"
                "%{customdata[7]}  %{customdata[8]}<br>"
                "Distance: %{customdata[1]} ft<br>"
                "Angle: %{customdata[2]}°<br>"
                "xG: %{customdata[3]}<br>"
                "Strength: %{customdata[4]}<br>"
                "Period: %{customdata[5]}"
                "<extra></extra>"
            ),
            name="Shots",
            showlegend=False,
        ))

    # Blocked shots
    if len(map_blocked_df) > 0:
        fig.add_trace(go.Scatter(
            x=map_blocked_df["x_coord"],
            y=map_blocked_df["y_coord"],
            mode="markers",
            marker=dict(
                symbol="x",
                color="rgba(255,255,255,0.25)",
                size=6,
                line=dict(width=1, color="rgba(255,255,255,0.25)"),
            ),
            customdata=np.column_stack([
                map_blocked_df["shot_distance"].round(1),
                map_blocked_df["shot_angle"].round(1),
                map_blocked_df["strength"],
                map_blocked_df["period"],
                map_blocked_df["date_str"],
                map_blocked_df["opp_label"],
            ]),
            hovertemplate=(
                "<b>Blocked Shot</b><br>"
                "%{customdata[4]}  %{customdata[5]}<br>"
                "Distance: %{customdata[0]} ft<br>"
                "Angle: %{customdata[1]}°<br>"
                "Strength: %{customdata[2]}<br>"
                "Period: %{customdata[3]}"
                "<extra></extra>"
            ),
            name="Blocked",
            showlegend=False,
        ))

    # Goals
    if len(map_goals_df) > 0:
        fig.add_trace(go.Scatter(
            x=map_goals_df["x_coord"],
            y=map_goals_df["y_coord"],
            mode="markers",
            marker=dict(
                symbol="star",
                color=primary,
                size=16,
                opacity=1.0,
                line=dict(color="white", width=1.5),
            ),
            customdata=np.column_stack([
                map_goals_df["shot_distance"].round(1),
                map_goals_df["shot_angle"].round(1),
                map_goals_df["x_goal"].round(3),
                map_goals_df["strength"],
                map_goals_df["period"],
                map_goals_df["highlight_clip_url"].fillna(""),
                map_goals_df["date_str"],
                map_goals_df["opp_label"],
            ]),
            hovertemplate=(
                "<b>GOAL ⭐</b><br>"
                "%{customdata[6]}  %{customdata[7]}<br>"
                "Distance: %{customdata[0]} ft<br>"
                "Angle: %{customdata[1]}°<br>"
                "xG: %{customdata[2]}<br>"
                "Strength: %{customdata[3]}<br>"
                "Period: %{customdata[4]}"
                "<extra></extra>"
            ),
            name="Goals",
            showlegend=False,
        ))

    fig.update_layout(clickmode="event")
    return fig


def build_percentile_wheel(
    categories: list,
    values: list,
    r: int,
    g: int,
    b: int,
    primary: str,
) -> go.Figure:
    bar_colors = [
        get_performance_color(v, {"high": 67, "medium": 34})
        for v in values
    ]

    wheel = go.Figure()

    # Reference rings at 25, 50, 75
    for ref in [25, 50, 75]:
        wheel.add_trace(go.Scatterpolar(
            r=[ref] * (len(categories) + 1),
            theta=categories + [categories[0]],
            mode="lines",
            line=dict(color="rgba(255,255,255,0.2)", width=1, dash="dot"),
            showlegend=False,
            hoverinfo="skip",
        ))

    # Player percentile polygon
    wheel.add_trace(go.Scatterpolar(
        r=values + [values[0]],
        theta=categories + [categories[0]],
        fill="toself",
        fillcolor=f"rgba({r},{g},{b},0.18)",
        line=dict(color=primary, width=2),
        mode="lines+markers+text",
        marker=dict(color=bar_colors + [bar_colors[0]], size=10, line=dict(color="white", width=1.5)),
        text=[str(v) for v in values] + [str(values[0])],
        textposition="top center",
        textfont=dict(color="white", size=11, family="monospace"),
        showlegend=False,
    ))

    wheel.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True, range=[0, 100],
                tickvals=[25, 50, 75],
                ticktext=["25", "50", "75"],
                tickfont=dict(size=9, color="rgba(255,255,255,0.3)"),
                gridcolor="rgba(255,255,255,0.08)",
                linecolor="rgba(255,255,255,0.1)",
            ),
            angularaxis=dict(
                tickfont=dict(size=12, color="rgba(255,255,255,0.75)"),
                gridcolor="rgba(255,255,255,0.08)",
                linecolor="rgba(255,255,255,0.1)",
            ),
            bgcolor="#0D1B35",
        ),
        paper_bgcolor="#0A0E1A",
        font_color="white",
        showlegend=False,
        margin=dict(l=55, r=55, t=30, b=30),
        height=380,
    )

    return wheel


def build_shot_type_breakdown(
    type_df: pd.DataFrame,
    selected_shot_type,
    r: int,
    g: int,
    b: int,
) -> go.Figure:
    dot_colors = [
        get_performance_color(v, {"high": 15, "medium": 8})
        for v in type_df["sh_pct"]
    ]

    # Generate bar colors based on selection state
    bar_fill_colors = []
    bar_line_colors = []
    for shot_type in type_df["shot_type"]:
        is_selected = shot_type == selected_shot_type
        fill = f"rgba({r},{g},{b},0.7)" if is_selected else f"rgba({r},{g},{b},0.3)"
        line = f"rgba({r},{g},{b},1.0)" if is_selected else f"rgba({r},{g},{b},0.6)"
        bar_fill_colors.append(fill)
        bar_line_colors.append(line)

    fig = go.Figure()

    # Volume % bars
    fig.add_trace(go.Bar(
        x=type_df["shots"],
        y=type_df["shot_type"],
        orientation="h",
        marker=dict(
            color=bar_fill_colors,
            line=dict(color=bar_line_colors, width=1),
        ),
        text=[f"{v}%" for v in type_df["volume_pct"]],
        textposition="outside",
        textfont=dict(color="rgba(255,255,255,0.6)", size=11),
        hovertemplate="<b>%{y}</b><br>Shots: %{x}<br>Volume: %{text}<extra></extra>",
        showlegend=False,
    ))

    # Shooting % efficiency dots
    fig.add_trace(go.Scatter(
        x=type_df["shots"],
        y=type_df["shot_type"],
        mode="markers",
        marker=dict(color=dot_colors, size=10, line=dict(color="white", width=1.5)),
        customdata=type_df["sh_pct"],
        hovertemplate="<b>%{y}</b><br>Sh%: %{customdata}%<extra></extra>",
        showlegend=False,
    ))

    fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, fixedrange=True)
    fig.update_yaxes(showgrid=False, zeroline=False, fixedrange=True,
                     tickfont=dict(color="rgba(255,255,255,0.75)", size=12))

    layout = get_dark_layout(height=280, margin_l=0, margin_r=60, margin_t=10, margin_b=10)
    layout["bargap"] = 0.3
    fig.update_layout(**layout)

    return fig
