from sqlalchemy.orm import Session

from app.services.fhir_repository import conditions_for_patient, observations_for_patient


class PatientContextService:
    def _build_context(self, patient_id: str, conditions: list[dict], observations: list[dict]) -> dict:
        latest = max(observations, key=lambda item: item.get("observed_on", ""), default=None)

        return {
            "patient_id": patient_id,
            "context": {
                "conditions": [condition["display"].lower() for condition in conditions],
                "last_bp": f"{int(latest['systolic'])}/{int(latest['diastolic'])}" if latest else "unknown",
                "last_visit": latest["observed_on"] if latest else None,
            },
            "goal": "manage hypertension",
            "tasks": [],
        }

    def build_context(self, db: Session, patient_id: str) -> dict:
        conditions = conditions_for_patient(db, patient_id)
        observations = observations_for_patient(db, patient_id)
        return self._build_context(patient_id, conditions, observations)

    def build_context_from_records(self, patient_id: str, conditions: list[dict], observations: list[dict]) -> dict:
        return self._build_context(patient_id, conditions, observations)
