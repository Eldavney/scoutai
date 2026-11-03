# ScoutAI: automatic football predictions

Every morning this project checks real results, marks each pick ✅ or ❌, loads new matches, makes predictions, learns from its record, and sends a notification to your phone. The website updates by itself.

## What it does (in plain words)
- **07:00 Lagos time:** gets yesterday's final scores, marks every pick, loads today's and tomorrow's matches, and sends you a phone notification with yesterday's result and today's top 3 picks.
- **11:30, 14:30, 17:30 and 20:30:** re-checks injuries and line-ups for matches that haven't started and updates the picks.
- **Never changes a pick after kick-off.** Matches it didn't predict in time are skipped, not filled in afterwards.
- **Learns privately:** it measures its own accuracy and trims its confidence when it has been too high. The notes live in the `private` folder and are never shown on the website. (If your GitHub repository is public, anyone can still read the files in it, so keep it private if you want the learning notes hidden.)

## How the predictions are built now
The main driver is each team's **current form and strength**, not its reputation. Data comes from three places:
- **API-Football** (the paid feed): fixtures, results, last-6 matches, home/away splits, head-to-head, injuries, line-ups, odds, and xG where available.
- **ClubElo** (free, `clubelo.com`): one strength rating for clubs in every European league. This is what lets Champions League and Europa League ties be compared fairly, because domestic goals per game aren't comparable across leagues.
- **Understat** (optional, off by default): xG for the top five leagues. Turn it on with `USE_UNDERSTAT=1`. It works by scraping, whose terms are a grey area, so use it at your own risk.

For each match:
- **Same-league games:** 40% form model (last 6, home/away splits, xG), 20% Elo strength, 40% market.
- **Cross-league games** (Champions, Europa, Conference League): 15% form, 40% Elo, 45% market.
- **Head-to-head** (last 6 meetings, capped at 3 points) and **team news** (injuries, capped at 4 points, plus Claude's optional review) are added on top.
- Any match where my form/strength view and the market differ by 12+ points is flagged.
Weights live in `backend/config.py`. Set `FORM_MODEL=0` to go back to the older, simpler method. Club names are matched to ClubElo carefully, and a club that can't be matched with confidence is left out rather than guessed.
Run the checks with `python tests/test_sources.py`.

## Set-up (about 20 minutes, no coding)
1. Create a free account at github.com and make a new repository (for example `scoutai`). Upload everything in this folder, keeping the folders as they are.
2. Get a key at api-football.com (free plan: 100 requests a day, enough for roughly 25 matches a day; a paid plan is needed for all 21 competitions every day).
3. In your repository: **Settings → Secrets and variables → Actions → New repository secret**. Add:
   - `API_FOOTBALL_KEY` — your key from step 2
   - `NTFY_TOPIC` — a private random name, for example `scoutai-rod6-7f3k9`
   - `ANTHROPIC_API_KEY` — optional. If added, Claude reviews every match (injuries, form, line-ups) and can nudge each probability by at most 6 points. If left out, the maths model runs alone.
4. **Settings → Pages:** Source "Deploy from a branch", branch `main`, folder `/docs`. Your site address appears there.
5. **Actions → ScoutAI update → Run workflow** (mode `morning`) to run it the first time.
6. Install the free **ntfy** app on your phone and subscribe to your topic name to get the daily notification.

## Check the league numbers first
League ids come from memory and must be verified. Run:
`python backend/find_leagues.py "Champions League Two"`
Add AFC Champions League Two to `backend/config.py` using the id it prints, and check the others the same way.

## Things to know
- This has been tested with simulated data only, not the live API. The form model pulls about 10 requests per match (more with xG), so a paid data plan is needed for all competitions every day. Expect to fix small things on the first real run.
- Free data coverage differs by league. Süper Lig, Saudi Pro League, Scottish Championship and USL may have thinner predictions.
- The site is public if the repository is public. Anyone with the link can see your picks.
- Results use the 90-minute score, so extra time and penalties don't count.
- No method wins every time. Judge it on the Record tab after at least 100 settled picks.
