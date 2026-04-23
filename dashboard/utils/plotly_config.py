def get_dark_layout(height: int = 280, margin_l: int = 40, margin_r: int = 20, margin_t: int = 10, margin_b: int = 30) -> dict:
    return {
        "paper_bgcolor": "rgba(0,0,0,0)",
        "plot_bgcolor": "rgba(0,0,0,0)",
        "margin": dict(l=margin_l, r=margin_r, t=margin_t, b=margin_b),
        "height": height,
    }


def get_dark_xaxes(title: str = "", show_grid: bool = False) -> dict:
    return {
        "showgrid": show_grid,
        "zeroline": False,
        "tickfont": dict(color="rgba(255,255,255,0.4)", size=10),
        "title": dict(text=title, font=dict(color="rgba(255,255,255,0.4)", size=11)) if title else {},
        "fixedrange": True,
    }


def get_dark_yaxes(title: str = "", show_grid: bool = True) -> dict:
    return {
        "showgrid": show_grid,
        "gridcolor": "rgba(255,255,255,0.06)" if show_grid else None,
        "zeroline": False,
        "tickfont": dict(color="rgba(255,255,255,0.4)", size=10),
        "title": dict(text=title, font=dict(color="rgba(255,255,255,0.4)", size=11)) if title else {},
        "fixedrange": True,
    }


def generate_bar_colors_for_selection(df_values, r: int, g: int, b: int, selected_value=None, selected_active: bool = False) -> list:
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
