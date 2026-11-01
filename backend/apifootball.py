"""Thin API-Football v3 client (https://www.api-football.com). Needs API_FOOTBALL_KEY."""
import os, requests
BASE = "https://v3.football.api-sports.io"

def get(path, **params):
    r = requests.get(BASE + path, params=params, headers={"x-apisports-key": os.environ["API_FOOTBALL_KEY"]}, timeout=30)
    r.raise_for_status(); j = r.json()
    if j.get("errors"): raise RuntimeError(f"API-Football error on {path}: {j['errors']}")
    return j.get("response", [])

def dig(d, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and k in d and d[k] is not None: d = d[k]
        else: return default
    return d
