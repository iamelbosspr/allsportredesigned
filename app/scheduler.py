from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger


class PriceScheduler:
    def __init__(self, service, timezone: str, hours: str) -> None:
        self.service = service
        self.scheduler = BackgroundScheduler(timezone=timezone)
        self.hours = hours

    def start(self) -> None:
        self.scheduler.add_job(
            self._run_job,
            trigger=CronTrigger(hour=self.hours, minute=0),
            id="daco_sync",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )
        self.scheduler.start()

    def stop(self) -> None:
        if self.scheduler.running:
            self.scheduler.shutdown(wait=False)

    def run_once(self) -> dict:
        return self._run_job()

    def _run_job(self) -> dict:
        try:
            result = self.service.sync_from_daco()
            print(f"[scheduler] sync result: {result}")
            return result
        except Exception as exc:  # pragma: no cover
            print(f"[scheduler] sync failed: {exc}")
            return {"error": str(exc)}
