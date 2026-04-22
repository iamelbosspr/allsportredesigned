# Puerto Rico Gas Tracker (DACO)

This app tracks Puerto Rico gasoline prices directly from DACO and stores historical changes in SQLite.

## Features

- Pulls fuel prices directly from DACO:
  - Source page: `https://www.daco.pr.gov/recursos/estudios-economicos/datos-de-combustible/`
- Scheduled automatic updates at Puerto Rico local time:
  - `00:00`, `08:00`, `13:00`, `20:00`
- Stores only changed snapshots (so history reflects actual movement up/down)
- Dashboard with:
  - Latest prices by brand (regular, premium, diesel)
  - Trend direction vs previous snapshot (up/down/no change)
  - Historical chart by brand and fuel type
- JSON API endpoints for integrations

## Quick start

1. Create and activate a virtual environment.
2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Run:

```bash
python -m app.main
```

4. Open:

`http://127.0.0.1:5000`

## API

- `GET /api/latest`
  - Latest snapshot + trend deltas
- `GET /api/history?brand=Total&fuel=regular&days=90`
  - Historical time series for a brand/fuel
- `POST /api/sync`
  - Manual sync from DACO

## Notes

- Time zone for schedule is `America/Puerto_Rico`.
- Data is persisted in `gas_prices.db` in this project folder.
- Keep the app process running continuously so scheduler jobs execute.
