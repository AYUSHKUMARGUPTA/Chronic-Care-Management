from datetime import date, datetime

from pydantic import BaseModel, Field, ConfigDict


class PatientOut(BaseModel):
    id: str
    external_id: str
    full_name: str
    birth_date: date | None
    gender: str | None

    class Config:
        from_attributes = True


class AlertOut(BaseModel):
    id: int
    patient_id: str = Field(alias="patient_resource_id")
    alert_type: str
    severity: str
    message: str
    status: str
    approved_by: str | None = None
    approved_at: datetime | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class PatientSummaryOut(BaseModel):
    patient_id: str
    risk_level: str
    alerts: list[str]
    summary: str
    context: dict


class ClinicianPatientCard(BaseModel):
    patient_id: str
    full_name: str
    risk_level: str
    last_bp: str
    alerts: list[str]


class BPTrendPoint(BaseModel):
    observed_on: str
    systolic: float
    diastolic: float
