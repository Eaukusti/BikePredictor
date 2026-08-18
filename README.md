# BikePredictor
# Helsinki City Bike Availability Predictor

A weekend project: is there going to be a bike (or a free dock) at my
station when I get there? Built on HSL's live city bike data.

## Architecture

```
GitHub repo
├── src/digitransit_client.py   → calls HSL's live GraphQL API
├── src/poll_and_log.py         → snapshots + appends to data/history.csv
├── .github/workflows/poll.yml  → runs poll_and_log.py every 15 min, commits the result
├── app.py                      → Streamlit frontend (live status + trend)
└── data/history.csv            → accumulated history (created by the workflow)
```

Two things are happening at once:
1. **Right now:** `app.py` calls the Digitransit API directly on every page
   load, so the "bikes available now" numbers are always live.
2. **Over time:** a scheduled GitHub Action polls the same API independently
   and appends each snapshot to `data/history.csv`, which is what lets the
   app show a trend — and eventually a real prediction — instead of just a
   single live number.

## Build steps

**Setup (30–60 min)**
1. Get a free API key at https://portal-api.digitransit.fi/
2. Create a new GitHub repo, add these files, open it in a Codespace.
3. `pip install -r requirements.txt`
4. `export DIGITRANSIT_API_KEY=...` and run `python src/digitransit_client.py`
   to sanity-check the API call works before building anything on top of it.

**Get the pipeline running (1–2 hrs)**
5. Add `DIGITRANSIT_API_KEY` as a repo secret: Settings → Secrets and
   variables → Actions → New repository secret.
6. Commit `.github/workflows/poll.yml`. Trigger it once manually
   (Actions tab → Poll city bike stations → Run workflow) to confirm it
   writes `data/history.csv` and commits it back.
7. Let it run in the background (every 15 min) while you work on the rest —
   by the time you're done with the frontend you'll already have hours of
   real history to test against.

**Frontend (1–2 hrs)**
8. `streamlit run app.py` locally, confirm the live numbers and the trend
   chart both work.

**The actual analysis — this is the part that's yours (remaining time)**
9. Replace the TODO in `app.py` with a real short-term prediction. Start
   with the naive version (recent average), then try the day-of-week /
   hour-of-day baseline once you have a few days of history — that's
   usually the biggest jump in usefulness for the least code.

**Ship it (30 min)**
10. Push to GitHub, connect the repo at https://share.streamlit.io
    (Streamlit Community Cloud), add `DIGITRANSIT_API_KEY` as a secret
    there too. Every future push redeploys automatically.
11. Write up *why* you made the choices you did (this file is a start) —
    for a solution-design-flavored portfolio, the reasoning matters as
    much as the code.

## Notes / things that could trip you up

- The GraphQL schema has changed before (an older `BikeRentalStation`
  type was deprecated in favor of `VehicleRentalStation`). If a query
  errors, check the field names in the live GraphiQL explorer linked in
  `digitransit_client.py` before assuming your code is wrong.
- `history.csv` only exists after the GitHub Action has run at least
  once — the app handles that gracefully, but don't be surprised by an
  empty trend chart on a fresh repo.
