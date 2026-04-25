import os
from pathlib import Path
import httpx
import streamlit as st

_env_file = Path(__file__).parent.parent.parent / ".env"
if _env_file.exists():
    for _line in _env_file.read_text().splitlines():
        if "=" in _line and not _line.startswith("#"):
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())


def get_secret(key: str) -> str:
    try:
        return st.secrets.get(key) or ""
    except Exception:
        return os.environ.get(key, "")


def resolve_mp4(sharing_url: str) -> str | None:
    account_id = get_secret("ACCOUNT_ID") or os.environ.get("ACCOUNT_ID", "")
    policy_key = get_secret("POLICY_KEY") or os.environ.get("POLICY_KEY", "")
    if not policy_key:
        return None
    try:
        content_id = sharing_url.rstrip("/").split("-")[-1]
        r = httpx.get(
            f"https://edge.api.brightcove.com/playback/v1/accounts/{account_id}/videos/{content_id}",
            headers={"BCOV-Policy": policy_key},
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


@st.cache_data(ttl=300, show_spinner=False)
def get_video_url(sharing_url: str) -> str | None:
    return resolve_mp4(sharing_url)
