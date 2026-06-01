from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.observation import Observation
from app.models.patient import Condition, Medication, Patient
from app.schemas.ingestion import FhirBundleIn


class IngestionAgent:
    """Converts FHIR-like payloads into normalized internal records."""

    def ingest_bundle(self, db: Session, bundle: FhirBundleIn, commit: bool = True) -> Patient:
        patient = db.scalar(select(Patient).where(Patient.external_id == bundle.patient.external_id))
        if patient is None:
            patient = Patient(
                external_id=bundle.patient.external_id,
                full_name=bundle.patient.full_name,
                birth_date=bundle.patient.birth_date,
                gender=bundle.patient.gender,
            )
            db.add(patient)
            db.flush()
        else:
            patient.full_name = bundle.patient.full_name
            patient.birth_date = bundle.patient.birth_date
            patient.gender = bundle.patient.gender

        for condition in bundle.conditions:
            db.add(
                Condition(
                    patient_id=patient.id,
                    code=condition.code,
                    display=condition.display,
                    clinical_status=condition.clinical_status,
                )
            )

        for medication in bundle.medications:
            db.add(
                Medication(
                    patient_id=patient.id,
                    code=medication.code,
                    display=medication.display,
                    status=medication.status,
                )
            )

        for observation in bundle.observations:
            db.add(
                Observation(
                    patient_id=patient.id,
                    obs_type="systolic",
                    value=observation.systolic,
                    unit="mmHg",
                    observed_on=observation.observed_on,
                )
            )
            db.add(
                Observation(
                    patient_id=patient.id,
                    obs_type="diastolic",
                    value=observation.diastolic,
                    unit="mmHg",
                    observed_on=observation.observed_on,
                )
            )

        db.flush()
        if commit:
            db.commit()
        db.refresh(patient)
        return patient
