# ScoutAI: automatic football predictions

Every morning this project checks real results, marks each pick ✅ or ❌, loads new matches, makes predictions, learns from its record, and sends a notification to your phone. The website updates by itself.

## What it does (in plain words)
- **07:00 Lagos time:** gets yesterday's final scores, marks every pick, loads today's and tomorrow's matches, and sends you a phone notification with yesterday's result and today's top 3 picks.
- **11:30, 14:30, 17:30 and 20:30:** re-checks injuries and line-ups for matches that haven't started and updates the picks.
- **Never changes a pick after kick-off.** Matches it didn't predict in time are skipped, not filled in afterwards.
- **Learns:** after 30 settled picks, if its confidence has been too high, it trims future confidence automatically.

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
- This has been tested with simulated data only, not the live API. Expect to fix small things on the first real run.
- Free data coverage differs by league. Süper Lig, Saudi Pro League, Scottish Championship and USL may have thinner predictions.
- The site is public if the repository is public. Anyone with the link can see your picks.
- Results use the 90-minute score, so extra time and penalties don't count.
- No method wins every time. Judge it on the Record tab after at least 100 settled picks.
