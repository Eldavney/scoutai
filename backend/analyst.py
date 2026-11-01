"""Optional: Claude reviews the model's numbers plus injuries and line-ups. Needs ANTHROPIC_API_KEY.
Claude may only nudge each probability by +/-6 points and may only use the facts it is given."""
import os, json, requests
SYS = ("You are a careful football analyst. You get a match with model probabilities, form and injury data. "
       "Use ONLY the data given; never invent news. Reply with JSON only: "
       '{"adjust":{"home":int,"draw":int,"away":int},"note":"one plain sentence","flag":"one short warning or empty"}. '
       "Adjustments are percentage points between -6 and 6 and should add to about 0.")

def review(ctx):
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key: return None
    try:
        r = requests.post("https://api.anthropic.com/v1/messages", timeout=60,
            headers={"x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5"), "max_tokens": 400, "system": SYS,
                  "messages": [{"role": "user", "content": json.dumps(ctx, ensure_ascii=False)}]})
        r.raise_for_status()
        txt = "".join(b.get("text", "") for b in r.json()["content"])
        out = json.loads(txt[txt.index("{"): txt.rindex("}") + 1])
        adj = {k: max(-6, min(6, int(out["adjust"].get(k, 0)))) for k in ("home", "draw", "away")}
        return {"adjust": adj, "note": str(out.get("note", ""))[:240], "flag": str(out.get("flag", ""))[:160]}
    except Exception as e:
        print("analyst skipped:", e); return None
