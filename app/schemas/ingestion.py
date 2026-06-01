from datetime import date

from pydantic import BaseModel


class FhirPatientIn(BaseModel):
    external_id: str
    full_name: str
    birth_date: date | None = None
    gender: str | None = None


class FhirConditionIn(BaseModel):
    code: str
    display: str
    clinical_status: str | None = "active"


class FhirMedicationIn(BaseModel):
    code: str | None = None
    display: str
    status: str | None = "active"


class FhirObservationIn(BaseModel):
    systolic: float
    diastolic: float
    observed_on: date


class FhirBundleIn(BaseModel):
    patient: FhirPatientIn
    conditions: list[FhirConditionIn] = []
    medications: list[FhirMedicationIn] = []
    observations: list[FhirObservationIn] = []
