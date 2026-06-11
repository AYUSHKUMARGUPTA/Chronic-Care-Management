from typing import List
from contextlib import suppress

from sqlalchemy.orm import Session

from app.agents.monitoring_agent import MonitoringAgent
from app.models.alert import Alert
from app.services.patient_context import PatientContextService
from app.memory.context_store import save_memory
from app.api.websocket import broadcast_alert
from app.services.fhir_repository import medications_for_patient, observations_for_patient


class OrchestratorAgent:
    """Centralized orchestrator that runs ingestion->monitoring->reasoning workflows
    and emits provisional alerts requiring clinician approval.
    """

    def __init__(self):
        self.monitor = MonitoringAgent()
        # ReasoningAgent performs online LLM calls; instantiate lazily
        # in run_for_patient to avoid initializing the LLM at import/startup.
        self.reasoner = None
        self.context_service = PatientContextService()

    def run_for_patient(self, db: Session, patient_id: str) -> List[Alert]:
        observations = observations_for_patient(db, patient_id)
        medications = medications_for_patient(db, patient_id)

        findings = self.monitor.evaluate(observations, medications)

        # Build context and persist snapshot
        context = self.context_service.build_context(db, patient_id)
        save_memory(db, patient_id, {"context": context, "findings": findings})

        # Instantiate the ReasoningAgent on-demand so the orchestrator can
        # operate without requiring the online LLM to be available at
        # application start. Import lazily to avoid importing the LLM
        # client module at startup.
        if self.reasoner is None:
            from app.agents.reasoning_agent import ReasoningAgent

            self.reasoner = ReasoningAgent()

        summary = self.reasoner.summarize(context, findings)

        alerts: List[Alert] = []
        for finding in findings:
            alert = Alert(
                patient_resource_id=patient_id,
                alert_type=finding["type"],
                severity=finding.get("severity", "MEDIUM"),
                message=f"{finding.get('message')} -- Summary: {summary}",
                status="PROVISIONAL",
            )
            db.add(alert)
            alerts.append(alert)

        db.commit()

        # Broadcast provisional alerts to connected clinician clients
        for a in alerts:
            with suppress(ConnectionError, OSError, RuntimeError):
                broadcast_alert(
                    {
                        "id": a.id,
                        "patient_id": a.patient_resource_id,
                        "type": a.alert_type,
                        "severity": a.severity,
                        "message": a.message,
                        "status": a.status,
                    }
                )

        return alerts
