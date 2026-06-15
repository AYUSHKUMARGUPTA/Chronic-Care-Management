from sqlalchemy.orm import Session

from app.services.fhir_repository import conditions_for_patient, medications_for_patient, observations_for_patient


class PatientContextService:
    def _build_context(
        self,
        patient_id: str,
        conditions: list[dict],
        observations: list[dict],
        medications: list[dict] | None = None,
    ) -> dict:
        latest = max(observations, key=lambda item: item.get("observed_on", ""), default=None)
        active_medications = [
            med["display"]
            for med in (medications or [])
            if med.get("status") == "active" and med.get("display")
        ]

        return {
            "patient_id": patient_id,
            "context": {
                "conditions": [condition["display"].lower() for condition in conditions],
                "last_bp": f"{int(latest['systolic'])}/{int(latest['diastolic'])}" if latest else "unknown",
                "last_visit": latest["observed_on"] if latest else None,
                "active_medications": active_medications,
            },
            "goal": "manage hypertension",
            "tasks": [],
        }

    def build_context(self, db: Session, patient_id: str) -> dict:
        conditions = conditions_for_patient(db, patient_id)
        observations = observations_for_patient(db, patient_id)
        medications = medications_for_patient(db, patient_id)
        return self._build_context(patient_id, conditions, observations, medications)

    def build_context_from_records(
        self,
        patient_id: str,
        conditions: list[dict],
        observations: list[dict],
        medications: list[dict] | None = None,
    ) -> dict:
        return self._build_context(patient_id, conditions, observations, medications)
