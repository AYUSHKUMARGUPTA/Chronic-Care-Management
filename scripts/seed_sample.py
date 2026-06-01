import sys
from datetime import date, timedelta
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy.orm import Session

from app.agents.ingestion_agent import IngestionAgent
from app.db.session import SessionLocal
from app.schemas.ingestion import (
    FhirBundleIn,
    FhirConditionIn,
    FhirMedicationIn,
    FhirObservationIn,
    FhirPatientIn,
)


def main() -> None:
    db: Session = SessionLocal()
    agent = IngestionAgent()

    payload = FhirBundleIn(
        patient=FhirPatientIn(
            external_id="synthea-001",
            full_name="Alex Johnson",
            birth_date=date(1975, 6, 1),
            gender="male",
        ),
        conditions=[
            FhirConditionIn(code="38341003", display="Hypertensive disorder, systemic arterial")
        ],
        medications=[FhirMedicationIn(display="Lisinopril 10 MG Oral Tablet", status="active")],
        observations=[
            FhirObservationIn(
                systolic=150,
                diastolic=95,
                observed_on=date.today() - timedelta(days=40),
            )
        ],
    )

    patient = agent.ingest_bundle(db, payload)
    print(f"Seeded patient id={patient.id}, external_id={patient.external_id}")


if __name__ == "__main__":
    main()
