"""Learning loop. Measures how good the predictions really are and turns that into small, safe corrections.
Corrections only switch on once a category has enough settled matches, so a few lucky or unlucky games can't steer it."""
import json, os, glob, math
from model import judge, tier

MIN_N = 30            # settled matches before any correction is applied
BASE = [0.45, 0.26, 0.29]   # typical league home/draw/away rates, used as the "no skill" yardstick

def ptype(l):
    l = l.lower()
    if l.endswith("or draw"): return "double chance"
    if l.endswith("win"): return "outright win"
    if "goals" in l or "score" in l: return "goals"
    return "other"

def outcome(res): return 0 if res[0] > res[1] else 1 if res[0] == res[1] else 2

def brier(p, o): return sum((p[i] / 100 - (1 if i == o else 0)) ** 2 for i in range(3))

def metrics(matches):
    done = [m for m in matches if "res" in m]; n = len(done)
    out = {"n": n, "wins": 0, "by_type": {}, "by_tier": {}, "by_league": {}, "brier": None, "brier_base": None,
           "draw_pred": None, "draw_act": None, "fav_hit": None}
    if not n: return out
    b = bb = 0.0; dp = da = 0; fav = [0, 0]
    for m in done:
        ok = judge(m["picks"][0]["l"], *m["res"]); out["wins"] += ok
        for key, d in ((ptype(m["picks"][0]["l"]), out["by_type"]), (tier(m["picks"][0]["c"]), out["by_tier"]), (m["league"], out["by_league"])):
            d.setdefault(key, [0, 0]); d[key][1] += 1; d[key][0] += ok
        o = outcome(m["res"]); b += brier(m["p"], o); bb += brier([100 * x for x in BASE], o)
        dp += m["p"][1]; da += (o == 1)
        top = max(range(3), key=lambda i: m["p"][i])
        if top != 1 and m["p"][top] >= 55: fav[1] += 1; fav[0] += (o == top)
    out.update(brier=round(b / n, 3), brier_base=round(bb / n, 3), draw_pred=round(dp / n, 1), draw_act=round(100 * da / n, 1),
               fav_hit=fav)
    return out

def corrections(met):
    """Small, bounded fixes. Empty until there are MIN_N settled matches."""
    c = {"draw_scale": 1.0, "goals_penalty": 0}
    if met["n"] < MIN_N: return c
    if met["draw_pred"] and abs(met["draw_pred"] - met["draw_act"]) > 4:
        c["draw_scale"] = round(max(0.8, min(1.2, met["draw_act"] / met["draw_pred"])), 2)
    g = met["by_type"].get("goals")
    if g and g[1] >= 10 and g[0] / g[1] < 0.45: c["goals_penalty"] = 4
    return c

def run(data_dir, lessons_path=None):
    ms = []
    for p in glob.glob(os.path.join(data_dir, "fixtures", "*.json")): ms += json.load(open(p, encoding="utf-8"))["matches"]
    met = metrics(ms); met["corrections"] = corrections(met)
    if lessons_path and os.path.exists(lessons_path): met.update(json.load(open(lessons_path, encoding="utf-8")))
    json.dump(met, open(os.path.join(data_dir, "learning.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return met
