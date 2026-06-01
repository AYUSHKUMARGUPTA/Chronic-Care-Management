import asyncio
from contextlib import suppress
from app.db.session import SessionLocal
from app.services.alert_service import AlertService
from app.services.fhir_repository import list_patient_rows



alert_service = AlertService()


def run_scan_once() -> None:
    db = SessionLocal()
    try:
        patients = list_patient_rows(db)
        for patient in patients:
            with suppress(OSError, RuntimeError):
                alert_service.refresh_for_patient(db, patient["patient_id"])
    finally:
        db.close()


def start_background_monitor(app, interval_seconds: int = 60):
    """Register startup/shutdown handlers to run periodic orchestration."""

    async def _monitor_loop():
        while True:
            with suppress(OSError, RuntimeError):
                await asyncio.to_thread(run_scan_once)
            await asyncio.sleep(interval_seconds)

    def _on_startup():
        # schedule the monitor loop on the running event loop
        app.state.monitor_task = asyncio.create_task(_monitor_loop())

    def _on_shutdown():
        task = getattr(app.state, "monitor_task", None)
        if task:
            task.cancel()

    try:
        app.add_event_handler("startup", _on_startup)
        app.add_event_handler("shutdown", _on_shutdown)
    except AttributeError:
        # Fallback for FastAPI/Starlette versions without add_event_handler
        app.on_event("startup")(_on_startup)
        app.on_event("shutdown")(_on_shutdown)
