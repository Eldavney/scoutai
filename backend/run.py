"""ScoutAI daily job.
  python backend/run.py morning   -> settle results, load today+tomorrow, update calibration, send notification
  python backend/run.py refresh   -> re-check injuries/line-ups for matches that have not kicked off yet
Picks for a match are never changed once it has kicked off."""
import os, sys, json, glob, datetime as dt, requests
sys.path.insert(0, os.path.dirname(__file__))
from config import LEAGUES, TZ
from model import outcome_probs, to_ints, build_picks, judge, stats
from apifootball import get, dig
import analyst, learn

DATA = os.path.join(os.path.dirname(__file__), "..", "docs", "data")
FIN = {"FT", "AET", "PEN"}

def read(path, default):
    try: return json.load(open(path, encoding="utf-8"))
    except FileNotFoundError: return default

def write(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(obj, open(path, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

def day_path(d): return os.path.join(DATA, "fixtures", f"{d}.json")
def now_utc(): return dt.datetime.now(dt.timezone.utc)
def parse_ko(s): return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
def pct(s):
    try: return float(str(s).replace("%", "").strip())
    except ValueError: return 0.0

def day_fixtures(d):
    return [f for f in get("/fixtures", date=d) if f["league"]["id"] in LEAGUES]

# ---------- settle ----------
def settle():
    cal_changed = False
    for path in sorted(glob.glob(day_path("*"))):
        d = os.path.basename(path)[:-5]; doc = read(path, {"matches": []})
        pend = [m for m in doc["matches"] if "res" not in m and m.get("fid") and
                parse_ko(m["ko"]) < now_utc() - dt.timedelta(hours=3)]
        if not pend: continue
        by_id = {f["fixture"]["id"]: f for f in get("/fixtures", date=d)}
        for m in pend:
            f = by_id.get(m["fid"])
            if f and f["fixture"]["status"]["short"] in FIN:
                ft = f["score"]["fulltime"]            # 90-minute score
                if ft["home"] is not None: m["res"] = [ft["home"], ft["away"]]; cal_changed = True
        write(path, doc)
    return cal_changed

def all_matches():
    out = []
    for p in glob.glob(day_path("*")): out += read(p, {"matches": []})["matches"]
    return out

# ---------- predict ----------
def build_match(f, shrink, corr):
    fid = f["fixture"]["id"]; ko = f["fixture"]["date"]
    pr = (get("/predictions", fixture=fid) or [{}])[0]
    pc = dig(pr, "predictions", "percent", default={}) or {}
    api = [pct(pc.get("home")), pct(pc.get("draw")), pct(pc.get("away"))]
    ha = float(dig(pr, "teams", "home", "league", "goals", "for", "average", "home", default=1.4) or 1.4)
    ad = float(dig(pr, "teams", "away", "league", "goals", "against", "average", "away", default=1.3) or 1.3)
    aa = float(dig(pr, "teams", "away", "league", "goals", "for", "average", "away", default=1.1) or 1.1)
    hd = float(dig(pr, "teams", "home", "league", "goals", "against", "average", "home", default=1.2) or 1.2)
    xh, xa = round((ha + ad) / 2, 2), round((aa + hd) / 2, 2)
    pois = outcome_probs(xh, xa)
    p = [0.6 * api[i] + 0.4 * pois[i] for i in range(3)] if sum(api) > 50 else pois
    inj = get("/injuries", fixture=fid); hid, aid = f["teams"]["home"]["id"], f["teams"]["away"]["id"]
    n_inj = {hid: len({x["player"]["id"] for x in inj if x["team"]["id"] == hid}),
             aid: len({x["player"]["id"] for x in inj if x["team"]["id"] == aid})}
    flags = []
    for tid, side, other in ((hid, 0, 2), (aid, 2, 0)):
        pts = min(4, max(0, n_inj[tid] - 2))
        if pts:
            p[side] -= pts; p[1] += pts / 2; p[other] += pts / 2
            flags.append(f"{f['teams']['home' if side == 0 else 'away']['name']} have {n_inj[tid]} players listed injured or suspended.")
    lu = get("/fixtures/lineups", fixture=fid); note = "Line-ups confirmed." if lu else ""
    ctx = {"match": f"{f['teams']['home']['name']} v {f['teams']['away']['name']}", "model_probs": [round(x) for x in p],
           "xg": [xh, xa], "api_advice": dig(pr, "predictions", "advice"), "form_home": dig(pr, "teams", "home", "league", "form"),
           "form_away": dig(pr, "teams", "away", "league", "form"), "injured_home": n_inj[hid], "injured_away": n_inj[aid],
           "lineups_confirmed": bool(lu)}
    rv = analyst.review(ctx)
    if rv:
        for i, k in enumerate(("home", "draw", "away")): p[i] += rv["adjust"][k]
        note = (rv["note"] + " " + note).strip()
        if rv["flag"]: flags.append(rv["flag"])
    p[1] *= corr.get('draw_scale', 1.0)          # learned: correct over- or under-rating of draws
    p = to_ints([max(2, x) for x in p])
    local = parse_ko(ko).astimezone(TZ)
    return {"home": f["teams"]["home"]["name"], "away": f["teams"]["away"]["name"], "league": LEAGUES[f["league"]["id"]],
            "time": local.strftime("%H:%M"), "ko": ko, "fid": fid, "p": p, "xg": [xh, xa],
            "z": [round(100 * 2.718281828 ** -xh), round(100 * 2.718281828 ** -xa)],
            "picks": build_picks(p, [xh, xa], shrink, corr.get("goals_penalty", 0)), "api": api, "n": note or "Form and injury data from API-Football.",
            "fl": " ".join(flags)}

def predict_day(d, shrink, corr):
    path = day_path(d); doc = read(path, {"matches": [], "tz": str(TZ)}); have = {m.get("fid"): m for m in doc["matches"] if m.get("fid")}
    keep = [m for m in doc["matches"] if not m.get("fid")]       # hand-made entries stay untouched
    out = []
    for f in day_fixtures(d):
        fid = f["fixture"]["id"]; old = have.get(fid)
        started = parse_ko(f["fixture"]["date"]) <= now_utc() + dt.timedelta(minutes=20)
        if old and (started or "res" in old): out.append(old); continue    # never rewrite after kick-off
        if started: continue                                                # not predicted in time: skip, do not back-fill
        try: out.append(build_match(f, shrink, corr))
        except Exception as e:
            print("skip", f["fixture"]["id"], e)
            if old: out.append(old)
    doc["matches"] = sorted(keep + out, key=lambda m: m["time"]); doc["tz"] = str(TZ); doc["updated"] = now_utc().isoformat(timespec="minutes")
    write(path, doc)

def write_index():
    days = sorted(os.path.basename(p)[:-5] for p in glob.glob(day_path("*")))
    coaches = sorted(os.path.basename(p)[:-5] for p in glob.glob(os.path.join(DATA, "coaches", "*.json")))
    write(os.path.join(DATA, "index.json"), {"days": days, "coaches": coaches})

# ---------- notify ----------
def notify(summary):
    topic = os.getenv("NTFY_TOPIC")
    if topic: requests.post(f"https://ntfy.sh/{topic}", data=summary.encode("utf-8"), headers={"Title": "ScoutAI daily update"}, timeout=20)
    print(summary)

def morning():
    settle()
    cal = stats(all_matches()); write(os.path.join(DATA, "calibration.json"), cal)
    corr = learn.run(DATA, os.path.join(DATA, "lessons.json"))["corrections"]   # measure, learn, write learning.json
    today = dt.datetime.now(TZ).date()
    for k in (0, 1): predict_day((today + dt.timedelta(days=k)).isoformat(), cal["shrink"], corr)
    write_index()
    yday = read(day_path((today - dt.timedelta(days=1)).isoformat()), {"matches": []})["matches"]
    done = [m for m in yday if "res" in m]; w = sum(judge(m["picks"][0]["l"], *m["res"]) for m in done)
    tm = sorted(read(day_path(today.isoformat()), {"matches": []})["matches"], key=lambda m: -m["picks"][0]["c"])[:3]
    lines = [f"Yesterday: {w} of {len(done)} top picks won. Overall {cal['wins']} of {cal['n']} ({cal['hit']}%)."]
    lines += [f"{m['home']} v {m['away']}: {m['picks'][0]['l']} ({m['picks'][0]['c']}%)" for m in tm]
    notify("\n".join(lines))

def refresh():
    cal = read(os.path.join(DATA, "calibration.json"), {"shrink": 0})
    corr = read(os.path.join(DATA, "learning.json"), {}).get("corrections", {})
    predict_day(dt.datetime.now(TZ).date().isoformat(), cal["shrink"], corr); write_index()

if __name__ == "__main__":
    {"morning": morning, "refresh": refresh}[sys.argv[1] if len(sys.argv) > 1 else "refresh"]()
