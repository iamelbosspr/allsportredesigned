from __future__ import annotations

import atexit
import os

from flask import Flask, jsonify, render_template, request

from .config import DACO_URL, DB_PATH, SCHEDULE_HOURS, TIMEZONE
from .db import get_history, init_db
from .scheduler import PriceScheduler
from .service import PriceService
from .site_content import NAV_ITEMS, PAGE_TARGETS, SITE_CONTENT


service = PriceService(db_path=DB_PATH, daco_url=DACO_URL)
scheduler = PriceScheduler(service=service, timezone=TIMEZONE, hours=SCHEDULE_HOURS)


def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates")

    init_db(DB_PATH)

    def render_site(page_key: str):
        return render_template(
            "index.html",
            active_page=page_key,
            initial_section=PAGE_TARGETS[page_key],
            nav_items=NAV_ITEMS,
            site=SITE_CONTENT,
        )

    @app.get("/")
    def index():
        return render_site("home")

    @app.get("/about-us")
    def about_us():
        return render_site("about")

    @app.get("/catalogs")
    def catalogs():
        return render_site("catalogs")

    @app.get("/locate-our-golf-products")
    def locations():
        return render_site("locations")

    @app.get("/price-lists")
    def price_lists():
        return render_site("price-lists")

    @app.get("/api/latest")
    def latest():
        data = service.get_latest_with_trends()
        if not data:
            return jsonify({"message": "No snapshots yet. Trigger /api/sync or wait for scheduler."}), 404
        return jsonify(data)

    @app.get("/api/history")
    def history():
        brand = request.args.get("brand")
        fuel = request.args.get("fuel", "regular").lower()
        days = int(request.args.get("days", "90"))

        if not brand:
            return jsonify({"error": "brand query parameter is required"}), 400

        try:
            rows = get_history(DB_PATH, brand=brand, fuel=fuel, days=days)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        return jsonify({"items": rows, "brand": brand, "fuel": fuel, "days": days})

    @app.post("/api/sync")
    def sync():
        result = service.sync_from_daco()
        return jsonify(result)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    _start_scheduler_once(app)
    return app


def _start_scheduler_once(app: Flask) -> None:
    if os.environ.get("DISABLE_SCHEDULER") == "1":
        return

    # In debug mode Flask starts a reloader process; only start scheduler in the main one.
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    if getattr(app, "_scheduler_started", False):
        return

    scheduler.start()
    scheduler.run_once()
    app._scheduler_started = True
    atexit.register(scheduler.stop)


if __name__ == "__main__":
    app = create_app()
    app.run(host="127.0.0.1", port=5000, debug=False)
