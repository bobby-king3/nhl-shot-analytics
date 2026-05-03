import plotly.graph_objects as go
import numpy as np
from dashboard.components.rink import make_rink_figure
from dashboard.utils.plotly_config import get_dark_layout, get_dark_xaxes, get_dark_yaxes, generate_bar_colors_for_selection
from dashboard.utils.styling import get_performance_color


def build_season_stats_table(season_log_df, selected_season, primary, r, g, b):
    def fmt_season(s):
        s = str(int(s))
        return f"{s[:4]}-{s[4:]}"

    def fmt_gax(v):
        if v is None:
            return "—"
        return f"+{v}" if v > 0 else str(v)

    header_cols = ["Season", "GP", "G", "SOG", "Sh%", "xG", "xG/GP", "GAX"]
    header_html = "".join(
        f"<th style='padding:6px 12px; color:rgba(255,255,255,0.45); font-size:11px; "
        f"text-transform:uppercase; letter-spacing:1px; font-weight:600; "
        f"text-align:{'left' if i == 0 else 'right'}'>{c}</th>"
        for i, c in enumerate(header_cols)
    )

    rows_html = ""
    for _, row in season_log_df.iterrows():
        is_current = row["season"] == selected_season
        bg = f"rgba({r},{g},{b},0.12)" if is_current else "transparent"
        border = f"border-left: 3px solid {primary};" if is_current else "border-left: 3px solid transparent;"
        weight = "700" if is_current else "400"
        color = "rgba(255,255,255,0.95)" if is_current else "rgba(255,255,255,0.6)"
        cells = [
            fmt_season(row["season"]), int(row["games_played"]), int(row["goals"]),
            int(row["shots_on_goal"]), f"{row['sh_pct']}%", row["total_xg"],
            row["xg_per_game"], fmt_gax(row["goals_above_expected"]),
        ]
        cells_html = "".join(
            f"<td style='padding:7px 12px; text-align:{'left' if i == 0 else 'right'}; "
            f"font-family:monospace; font-size:13px; color:{color}; font-weight:{weight}'>{v}</td>"
            for i, v in enumerate(cells)
        )
        rows_html += f"<tr style='background:{bg}; {border} transition:background 0.15s;'>{cells_html}</tr>"

    return f"""
    <div class="chart-card" style="margin-bottom:8px;">
      <div class="section-header">Season Stats</div>
      <table style="width:100%; border-collapse:collapse;">
        <thead><tr style="border-bottom:1px solid rgba(255,255,255,0.08)">{header_html}</tr></thead>
        <tbody>{rows_html}</tbody>
      </table>
    </div>
    """


def build_game_log_chart(game_log_df, selected_game_ids, game_filter_active, r, g, b, primary):
    rolling_avg = game_log_df["xg"].rolling(5, min_periods=1).mean()
    goal_games = game_log_df[game_log_df["goals"] > 0]

    bar_colors = generate_bar_colors_for_selection(
        game_log_df["game_id"],
        r, g, b,
        selected_value=None,
        selected_active=game_filter_active,
    )

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=game_log_df["game_num"],
        y=game_log_df["xg"],
        marker=dict(color=bar_colors, line=dict(width=0)),
        hovertemplate="Game %{x} vs %{customdata[0]}<br>%{customdata[1]}<br>xG: %{y:.3f}<extra></extra>",
        customdata=list(zip(game_log_df["opponent"], game_log_df["game_date"].dt.strftime("%b %d, %Y"))),
        showlegend=False,
    ))

    fig.add_trace(go.Scatter(
        x=game_log_df["game_num"],
        y=rolling_avg,
        mode="lines",
        line=dict(color="rgba(255,255,255,0.5)", width=2, dash="dot"),
        hovertemplate="Game %{x}<br>5-game avg: %{y:.3f}<extra></extra>",
        showlegend=False,
    ))

    if not goal_games.empty:
        fig.add_trace(go.Scatter(
            x=goal_games["game_num"],
            y=goal_games["xg"],
            mode="markers",
            marker=dict(symbol="star", color=primary, size=14, line=dict(color="white", width=1.5)),
            hovertemplate="Game %{x}<br>GOAL — xG: %{y:.3f}<extra></extra>",
            showlegend=False,
        ))

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


def build_shot_map(map_nongoals_df, map_blocked_df, map_goals_df, primary):
    fig = make_rink_figure(height=520)
    xg_vals = map_nongoals_df["x_goal"].fillna(0).clip(0, 0.5)

    if not map_nongoals_df.empty:
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

    if not map_blocked_df.empty:
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

    if not map_goals_df.empty:
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

    fig.update_layout(clickmode="event+select")
    return fig


def build_percentile_wheel(categories, values, r, g, b, primary):
    bar_colors = [
        get_performance_color(v, {"high": 67, "medium": 34})
        for v in values
    ]

    wheel = go.Figure()

    for ref in [25, 50, 75]:
        wheel.add_trace(go.Scatterpolar(
            r=[ref] * (len(categories) + 1),
            theta=categories + [categories[0]],
            mode="lines",
            line=dict(color="rgba(255,255,255,0.2)", width=1, dash="dot"),
            showlegend=False,
            hoverinfo="skip",
        ))

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


def build_shot_type_breakdown(type_df, selected_shot_type, r, g, b):
    bar_fill_colors = []
    bar_line_colors = []
    for shot_type in type_df["shot_type"]:
        is_selected = shot_type == selected_shot_type
        fill = f"rgba({r},{g},{b},0.8)" if is_selected else f"rgba({r},{g},{b},0.4)"
        line = f"rgba({r},{g},{b},1.0)" if is_selected else f"rgba({r},{g},{b},0.6)"
        bar_fill_colors.append(fill)
        bar_line_colors.append(line)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=type_df["volume_pct"],
        y=type_df["shot_type"],
        orientation="h",
        marker=dict(
            color=bar_fill_colors,
            line=dict(color=bar_line_colors, width=1),
        ),
        text=[f"{v}%" for v in type_df["volume_pct"]],
        textposition="outside",
        textfont=dict(color="rgba(255,255,255,0.7)", size=11),
        customdata=type_df["shots"],
        hovertemplate="<b>%{y}</b><br>%{x}% of shots (%{customdata} attempts)<extra></extra>",
        showlegend=False,
    ))

    fig.update_xaxes(showgrid=False, zeroline=False, showticklabels=False, fixedrange=True)
    fig.update_yaxes(showgrid=False, zeroline=False, fixedrange=True,
                     tickfont=dict(color="rgba(255,255,255,0.75)", size=12))

    layout = get_dark_layout(height=280, margin_l=0, margin_r=60, margin_t=10, margin_b=10)
    layout["bargap"] = 0.3
    fig.update_layout(**layout)
    return fig




def build_team_rolling_xgpct(game_log_df, r, g, b, primary):
    xg_total = game_log_df["xg_for"] + game_log_df["xg_against"]
    xg_pct = (game_log_df["xg_for"] / xg_total.replace(0, np.nan) * 100).fillna(50)
    rolling = xg_pct.rolling(10, min_periods=1).mean().round(1)
    game_num = game_log_df["game_num"].values

    ref = np.full(len(game_num), 50.0)
    above_50 = np.maximum(rolling.values, 50.0)
    below_50 = np.minimum(rolling.values, 50.0)

    fig = go.Figure()

    fig.add_trace(go.Scatter(x=game_num, y=above_50, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=game_num, y=ref, fill="tonexty", fillcolor=f"rgba({r},{g},{b},0.18)", mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=game_num, y=ref, mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(x=game_num, y=below_50, fill="tonexty", fillcolor="rgba(200,60,60,0.18)", mode="lines", line=dict(width=0), showlegend=False, hoverinfo="skip"))
    fig.add_trace(go.Scatter(
        x=game_num, y=rolling,
        mode="lines",
        line=dict(color=primary, width=2.5),
        hovertemplate="Game %{x}<br>10-game xG%: %{y:.1f}%<extra></extra>",
        showlegend=False,
    ))
    fig.add_hline(y=50, line=dict(color="rgba(255,255,255,0.35)", width=1, dash="dot"))
    fig.add_annotation(
        x=1, y=50, xref="paper", yref="y",
        text="50%", showarrow=False,
        font=dict(color="rgba(255,255,255,0.4)", size=10),
        xanchor="left", yanchor="middle",
        xshift=4,
    )

    fig.update_xaxes(**get_dark_xaxes(title="Game"))
    fig.update_yaxes(
        **get_dark_yaxes(title="xG%"),
        range=[35, 65],
        tickvals=[40, 50, 60],
        ticktext=["40%", "50%", "60%"],
    )
    layout = get_dark_layout(height=200, margin_l=50, margin_r=36, margin_t=10, margin_b=30)
    fig.update_layout(**layout)
    return fig



def build_streak_dots_grid(game_log_df) -> str:
    dots = []
    for row in game_log_df.itertuples():
        if row.result == "W":
            color, border = "#4CAF50", "#4CAF50"
        elif row.result == "OTL":
            color, border = "rgba(255,200,50,0.85)", "rgba(255,200,50,0.85)"
        else:
            color, border = "rgba(40,40,55,0.9)", "rgba(120,120,140,0.5)"
        label = f"{row.result} {'vs' if row.is_home else 'at'} {row.opponent} · {int(row.gf)}–{int(row.ga)}"
        dots.append(
            f"<div title='{label}' style='width:12px; height:12px; border-radius:50%;"
            f"background:{color}; border:1.5px solid {border};'></div>"
        )
    return (
        "<div style='display:grid; grid-template-columns: repeat(20, 12px); gap:5px; padding:4px 0 8px 0;'>"
        + "".join(dots)
        + "</div>"
    )


