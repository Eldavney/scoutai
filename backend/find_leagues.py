"""Prints API-Football league ids matching a name, e.g. python backend/find_leagues.py "AFC Champions League"."""
import sys
from apifootball import get
for x in get("/leagues", search=" ".join(sys.argv[1:]) or "Premier"):
    print(x["league"]["id"], x["league"]["name"], "-", x["country"]["name"])
