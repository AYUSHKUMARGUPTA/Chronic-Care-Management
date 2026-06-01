from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agents.orchestrator_agent import OrchestratorAgent
from app.services.fhir_repository import get_patient_row


class AlertService:
    def __init__(self):
        self.orchestrator = OrchestratorAgent()

    def _fetch_alerts(self, db: Session, where_clause: str = "", parameters: dict | None = None) -> list[dict]:
        query = """
            SELECT id, patient_resource_id, alert_type, severity, message, status, approved_by, approved_at, created_at
            FROM alerts
        """
        if where_clause:
            query += f" WHERE {where_clause}"
        query += " ORDER BY created_at DESC"

        rows = db.execute(text(query), parameters or {}).mappings().all()
        return [dict(row) for row in rows]

    def list_alerts_for_patient(self, db: Session, patient_id: str) -> list[dict]:
        return self._fetch_alerts(db, "patient_resource_id = :patient_id", {"patient_id": patient_id})

    def refresh_for_patient(self, db: Session, patient_id: str) -> list[dict]:
        # remove prior provisional alerts for the patient before re-evaluating
        db.execute(
            text(
                """
                DELETE FROM alerts
                WHERE patient_resource_id = :patient_id AND status = 'PROVISIONAL'
                """
            ),
            {"patient_id": patient_id},
        )
        db.commit()

        patient = get_patient_row(db, patient_id)
        if not patient:
            return []

        alerts = self.orchestrator.run_for_patient(db, patient_id)
        return alerts

    def list_alerts(self, db: Session) -> list[dict]:
        return self._fetch_alerts(db)
