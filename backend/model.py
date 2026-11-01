"""Prediction maths, pick rules, result checking and calibration. No network, easy to test."""
import math
from config import MAX_CONF

def _pois(l, k): return math.exp(-l) * l ** k / math.factorial(k)

def outcome_probs(xh, xa, n=9):
    h = d = a = 0.0
    for i in range(n + 1):
        for j in range(n + 1):
            p = _pois(xh, i) * _pois(xa, j)
            if i > j: h += p
            elif i == j: d += p
            else: a += p
    t = h + d + a
    return [100 * h / t, 100 * d / t, 100 * a / t]

def to_ints(v):
    t = sum(v) or 1
    r = [round(100 * x / t) for x in v]
    r[1] += 100 - sum(r)
    return r

def over25(xh, xa):
    l = xh + xa
    return 1 - math.exp(-l) * (1 + l + l * l / 2)

def build_picks(p, xg, shrink=0, goals_penalty=0):
    """p=[home,draw,away] ints, xg=[home,away]. Returns three picks, best first."""
    ph, pd, pa = p; xh, xa = xg; tot = xh + xa
    o = round(100 * over25(xh, xa)); b = round(100 * (1 - math.exp(-xh)) * (1 - math.exp(-xa)))
    goals = sorted([("Over 2.5 goals", o), ("Under 2.5 goals", 100 - o),
                    ("Both teams to score", b), ("Both teams not to score", 100 - b)], key=lambda x: -x[1])
    fav = "Home" if ph >= pa else "Away"; pf = max(ph, pa); dc = (ph + pd) if fav == "Home" else (pa + pd)
    gw = f"Expected total goals {tot:.1f} (xG {xh:.1f}-{xa:.1f})."
    if pf >= 50:
        P = [(f"{fav} win", pf, f"Blend gives {ph}/{pd}/{pa} and the xG edge backs the {fav.lower()} side."),
             (f"{fav} or draw", dc, "Covers the draw if the win slips; lower price."), (*goals[0], gw)]
    elif abs(ph - pa) <= 4:
        P = [(f"{fav} or draw", dc, "Coin-flip on the result, so the slight favourite or a draw is the safest cover."),
             (*goals[0], gw + " Goals leans have been unreliable so far."), (*goals[1], gw)]
    else:
        P = [(f"{fav} or draw", dc, f"Blend {ph}/{pd}/{pa}: not strong enough for an outright win pick."),
             (f"{fav} win", pf, "Outright result if you want a bigger price."), (*goals[0], gw)]
    pen = lambda l: goals_penalty if ("goals" in l or "score" in l) else 0
    return [{"l": l, "c": max(1, min(c, MAX_CONF) - shrink - pen(l)), "w": w} for l, c, w in P]

def judge(label, hg, ag):
    L = label.lower(); t = hg + ag
    return {"home win": hg > ag, "away win": ag > hg, "draw": hg == ag, "home or draw": hg >= ag,
            "away or draw": ag >= hg, "over 2.5 goals": t > 2.5, "under 2.5 goals": t < 2.5,
            "both teams to score": hg > 0 and ag > 0, "both teams not to score": hg == 0 or ag == 0}[L]

def tier(c): return "High" if c >= 65 else "Medium" if c >= 50 else "Low"

def stats(matches):
    """matches = every match dict that has 'res'. Returns record by tier and by league plus calibration."""
    n = w = 0; avg = 0.0; by = {}; lg = {}
    for m in matches:
        if "res" not in m: continue
        ok = judge(m["picks"][0]["l"], *m["res"]); n += 1; w += ok; avg += m["picks"][0]["c"]
        for key, d in ((tier(m["picks"][0]["c"]), by), (m["league"], lg)):
            d.setdefault(key, [0, 0]); d[key][1] += 1; d[key][0] += ok
    avg = avg / n if n else 0
    hit = 100 * w / n if n else 0
    shrink = 0
    if n >= 30 and hit < avg - 8: shrink = min(6, round((avg - hit) / 3))   # only after a real sample
    return {"n": n, "wins": w, "hit": round(hit, 1), "avg_conf": round(avg, 1), "by_tier": by,
            "by_league": lg, "shrink": shrink}
