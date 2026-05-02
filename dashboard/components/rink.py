import io
import base64
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import streamlit as st
from sportypy.surfaces.hockey import NHLRink

X_MIN, X_MAX = 24.0,  103.0
Y_MIN, Y_MAX = -43.5,  43.5

@st.cache_data(show_spinner=False)
def _get_rink_image():
    fig, ax = plt.subplots(figsize=(12, 8), facecolor="white")
    plt.subplots_adjust(left=0, right=1, top=1, bottom=0)
    ax.set_axis_off()

    rink = NHLRink()
    rink.draw(ax=ax, display_range="offense", xlim=(X_MIN, X_MAX), ylim=(Y_MIN, Y_MAX))

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=150, facecolor="white", bbox_inches="tight", pad_inches=0)
    plt.close(fig)
    buf.seek(0)

    return f"data:image/png;base64,{base64.b64encode(buf.read()).decode()}"

def make_rink_figure(height=460):
    fig = go.Figure()

    fig.add_layout_image(dict(
        source=_get_rink_image(),
        xref="x", yref="y",
        x=X_MIN, y=Y_MAX,
        sizex=X_MAX - X_MIN,
        sizey=Y_MAX - Y_MIN,
        sizing="stretch",
        layer="below",
        opacity=1.0,
    ))

    fig.update_xaxes(range=[X_MIN, X_MAX], showgrid=False, zeroline=False, showticklabels=False, fixedrange=True)
    fig.update_yaxes(range=[Y_MIN, Y_MAX], showgrid=False, zeroline=False, showticklabels=False, fixedrange=True,
                     scaleanchor="x", scaleratio=1)
    fig.update_layout(
        plot_bgcolor="white",
        paper_bgcolor="#0A0E1A",
        margin=dict(l=0, r=0, t=0, b=0),
        height=height,
        dragmode=False,
    )
    return fig
