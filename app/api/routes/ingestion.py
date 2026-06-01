from datetime import date, timedelta
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.agents.ingestion_agent import IngestionAgent
from app.db.session import get_db
from app.models.alert import Alert
from app.models.observation import Observation
from app.models.patient import Condition, Medication, Patient
from app.schemas.ingestion import (
    FhirBundleIn,
    FhirConditionIn,
    FhirMedicationIn,
    FhirObservationIn,
    FhirPatientIn,
)

router = APIRouter(prefix="/ingestion", tags=["ingestion"])
agent = IngestionAgent()


@router.post("/fhir")
def ingest_fhir_bundle(payload: FhirBundleIn, db: Session = Depends(get_db)):
    patient = agent.ingest_bundle(db, payload)
    return {
        "message": "bundle ingested",
        "patient": {
            "id": patient.id,
            "external_id": patient.external_id,
            "full_name": patient.full_name,
        },
    }


@router.post("/demo-seed")
def seed_demo_patient(db: Session = Depends(get_db)):
    suffix = str(uuid4())[:8]
    payload = FhirBundleIn(
        patient=FhirPatientIn(
            external_id=f"demo-{suffix}",
            full_name=f"Demo Patient {suffix}",
            birth_date=date(1978, 3, 14),
            gender="female",
        ),
        conditions=[
            FhirConditionIn(
                code="38341003",
                display="Hypertensive disorder, systemic arterial",
                clinical_status="active",
            )
        ],
        medications=[
            FhirMedicationIn(
                code="860975",
                display="Amlodipine 5 MG Oral Tablet",
                status="active",
            )
        ],
        observations=[
            FhirObservationIn(
                systolic=152,
                diastolic=94,
                observed_on=date.today() - timedelta(days=40),
            ),
            FhirObservationIn(
                systolic=146,
                diastolic=91,
                observed_on=date.today() - timedelta(days=15),
            ),
            FhirObservationIn(
                systolic=142,
                diastolic=89,
                observed_on=date.today() - timedelta(days=2),
            ),
        ],
    )
    patient = agent.ingest_bundle(db, payload)
    return {
        "message": "demo patient seeded",
        "patient": {
            "id": patient.id,
            "external_id": patient.external_id,
            "full_name": patient.full_name,
        },
    }


@router.delete("/demo-seed")
def reset_demo_patients(db: Session = Depends(get_db)):
    demo_patients = db.query(Patient).filter(Patient.external_id.like("demo-%")).all()
    demo_ids = [p.id for p in demo_patients]
    if not demo_ids:
        return {"message": "no demo patients found", "deleted_patients": 0}

    db.execute(delete(Alert).where(Alert.patient_id.in_(demo_ids)))
    db.execute(delete(Observation).where(Observation.patient_id.in_(demo_ids)))
    db.execute(delete(Condition).where(Condition.patient_id.in_(demo_ids)))
    db.execute(delete(Medication).where(Medication.patient_id.in_(demo_ids)))
    db.execute(delete(Patient).where(Patient.id.in_(demo_ids)))
    db.commit()

    return {"message": "demo patients reset", "deleted_patients": len(demo_ids)}
