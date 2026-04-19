"""Plotly chart configuration templates for consistent styling."""

import numpy as np


def get_dark_layout(height: int = 280, margin_l: int = 40, margin_r: int = 20, margin_t: int = 10, margin_b: int = 30) -> dict:
    """
    Get standard dark theme layout for Plotly charts.

    Args:
        height: Chart height in pixels
        margin_l, margin_r, margin_t, margin_b: Margins in pixels

    Returns:
        Layout configuration dict
    """
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "margin": dict(l=margin_l, r=margin_r, t=margin_t, b=margin_b),
        "height": height,
    }


def get_dark_xaxes(title: str = "", show_grid: bool = False) -> dict:
    """Get standard dark theme x-axis configuration."""
    return {
        "showgrid": show_grid,
        "zeroline": False,
        "tickfont": dict(color="rgba(255,255,255,0.4)", size=10),
        "title": dict(text=title, font=dict(color="rgba(255,255,255,0.4)", size=11)) if title else {},
        "fixedrange": True,
    }


def get_dark_yaxes(title: str = "", show_grid: bool = True) -> dict:
    """Get standard dark theme y-axis configuration."""
    return {
        "showgrid": show_grid,
        "gridcolor": "rgba(255,255,255,0.06)" if show_grid else None,
        "zeroline": False,
        "tickfont": dict(color="rgba(255,255,255,0.4)", size=10),
        "title": dict(text=title, font=dict(color="rgba(255,255,255,0.4)", size=11)) if title else {},
        "fixedrange": True,
    }


def generate_bar_colors_for_selection(
    df_values: list,
    r: int,
    g: int,
    b: int,
    selected_value=None,
    selected_active: bool = False,
) -> list[str]:
    """
    Generate bar colors based on selection state.

    Args:
        df_values: List of values to check against selection
        r, g, b: RGB values for the team color
        selected_value: The currently selected value (or None)
        selected_active: Whether filtering is currently active

    Returns:
        List of RGBA color strings
    """
    colors = []
    for val in df_values:
        is_selected = val == selected_value if selected_value is not None else False

        if not selected_active:
            colors.append(f"rgba({r},{g},{b},0.55)")
        elif is_selected:
            colors.append(f"rgba({r},{g},{b},0.75)")
        else:
            colors.append(f"rgba({r},{g},{b},0.35)")

    return colors
