"""Settings. League ids are API-Football ids. Run `python backend/find_leagues.py` to verify them."""
import os
from zoneinfo import ZoneInfo
TZ = ZoneInfo(os.getenv("SCOUTAI_TZ", "Africa/Lagos"))
MAX_CONF = 78                      # never claim more than this
LEAGUES = {
    39: "England - Premier League", 40: "England - Championship", 48: "England - EFL Cup",
    140: "Spain - LaLiga", 143: "Spain - Copa del Rey", 135: "Italy - Serie A",
    78: "Germany - Bundesliga", 61: "France - Ligue 1", 94: "Portugal - Liga Portugal",
    88: "Netherlands - Eredivisie", 90: "Netherlands - KNVB Beker", 203: "Türkiye - Süper Lig",
    307: "Saudi Arabia - Saudi Pro League", 180: "Scotland - Championship",
    255: "USA - USL Championship", 2: "International clubs - UEFA Champions League",
    3: "International clubs - UEFA Europa League", 848: "International clubs - UEFA Conference League",
    5: "International - UEFA Nations League", 10: "International - International Friendlies",
    # AFC Champions League Two: look up its id with find_leagues.py, then add it here
    # e.g. 1234: "International clubs - AFC Champions League Two",
}
