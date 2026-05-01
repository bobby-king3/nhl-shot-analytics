import httpx

BASE_URL = "https://api-web.nhle.com/v1"
STATS_BASE_URL = "https://api.nhle.com/stats/rest/en"


def get(path):
    url = f"{BASE_URL}{path}"
    response = httpx.get(url, timeout=30, follow_redirects=True)
    response.raise_for_status()
    return response.json()


def get_stats(path):
    url = f"{STATS_BASE_URL}{path}"
    response = httpx.get(url, timeout=30, follow_redirects=True)
    response.raise_for_status()
    return response.json()


def get_play_by_play(game_id):
    return get(f"/gamecenter/{game_id}/play-by-play")

def get_schedule():
    return get("/schedule/now")
