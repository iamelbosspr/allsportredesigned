from __future__ import annotations

from pathlib import Path

from .daco_client import fetch_daco_snapshot
from .db import get_latest_snapshot, get_previous_snapshot, insert_snapshot_if_changed


class PriceService:
    def __init__(self, db_path: Path, daco_url: str) -> None:
        self.db_path = db_path
        self.daco_url = daco_url

    def sync_from_daco(self) -> dict:
        snapshot = fetch_daco_snapshot(self.daco_url)
        inserted, snapshot_id = insert_snapshot_if_changed(self.db_path, snapshot)
        return {
            "inserted": inserted,
            "snapshot_id": snapshot_id,
            "source_updated_at": snapshot.source_updated_at.isoformat() if snapshot.source_updated_at else None,
            "brands": len(snapshot.prices),
        }

    def get_latest_with_trends(self) -> dict | None:
        latest = get_latest_snapshot(self.db_path)
        if not latest:
            return None

        previous = get_previous_snapshot(self.db_path, latest["id"])
        prev_by_brand = {
            p["brand"].lower(): p
            for p in (previous["prices"] if previous else [])
        }

        for row in latest["prices"]:
            prev = prev_by_brand.get(row["brand"].lower())
            row["trends"] = {
                "regular": _trend(row["regular"], prev["regular"] if prev else None),
                "premium": _trend(row["premium"], prev["premium"] if prev else None),
                "diesel": _trend(row["diesel"], prev["diesel"] if prev else None),
            }

        latest["previous_observed_at"] = previous["observed_at"] if previous else None
        return latest


def _trend(current: float, previous: float | None) -> dict:
    if previous is None:
        return {"delta": None, "direction": "n/a"}

    delta = round(current - previous, 4)
    if delta > 0:
        direction = "up"
    elif delta < 0:
        direction = "down"
    else:
        direction = "flat"

    return {
        "delta": delta,
        "direction": direction,
    }
