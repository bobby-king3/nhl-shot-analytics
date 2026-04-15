import os
import httpx
import streamlit as st

ACCOUNT_ID = os.environ.get("ACCOUNT_ID", "")
POLICY_KEY = os.environ.get("POLICY_KEY", "")
PLAYBACK_API = f"https://edge.api.brightcove.com/playback/v1/accounts/{ACCOUNT_ID}/videos"


@st.cache_data(ttl=300, show_spinner=False)
def get_mp4_url(sharing_url: str) -> str | None:
    if not POLICY_KEY:
        return None

    try:
        content_id = sharing_url.rstrip("/").split("-")[-1]
    except Exception:
        return None

    try:
        r = httpx.get(
            f"{PLAYBACK_API}/{content_id}",
            headers={"BCOV-Policy": POLICY_KEY},
            timeout=8,
        )
        r.raise_for_status()
        mp4s = [
            s for s in r.json().get("sources", [])
            if s.get("src", "").startswith("https") and ".mp4" in s.get("src", "")
        ]
        return mp4s[0]["src"] if mp4s else None
    except Exception:
        return None
