from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "gas_prices.db"
DACO_URL = "https://www.daco.pr.gov/recursos/estudios-economicos/datos-de-combustible/"
TIMEZONE = "America/Puerto_Rico"
SCHEDULE_HOURS = "0,8,13,20"
