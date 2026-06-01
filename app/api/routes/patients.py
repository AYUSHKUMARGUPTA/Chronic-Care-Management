from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from collections import defaultdict

from app.agents.monitoring_agent import MonitoringAgent
from app.db.session import get_db
from app.schemas.common import BPTrendPoint, ClinicianPatientCard, PatientOut, PatientSummaryOut
from app.services.alert_service import AlertService
from app.services.fhir_repository import (
    conditions_for_patient,
    get_patient_row,
    list_hypertension_condition_rows,
    list_latest_bp_per_patient,
    get_patient_rows_for_ids,
    observations_for_patient,
)
from app.services.patient_context import PatientContextService

router = APIRouter(prefix="/patients", tags=["patients"])
context_service = PatientContextService()
alert_service = AlertService()
monitoring_agent = MonitoringAgent()


def _risk_from_findings(findings: list[dict]) -> str:
    if not findings:
        return "LOW"
    if any(f.get("severity") == "HIGH" for f in findings):
        return "HIGH"
    return "MEDIUM"


@router.get("", response_model=list[PatientOut])
def list_patients(db: Session = Depends(get_db)):
    patients = list_patient_rows(db)
    return [
        {
            "id": patient["patient_id"],
            "external_id": patient["patient_id"],
            "full_name": patient["full_name"],
            "birth_date": patient["birth_date"],
            "gender": patient["gender"],
        }
        for patient in patients
    ]


@router.get("/{patient_id}/summary", response_model=PatientSummaryOut)
def get_patient_summary(patient_id: str, db: Session = Depends(get_db)):
    patient = get_patient_row(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    context = context_service.build_context(db, patient_id)
    alerts = alert_service.list_alerts_for_patient(db, patient_id)
    findings = monitoring_agent.evaluate(observations_for_patient(db, patient_id))
    # Instantiate the ReasoningAgent lazily so the dashboard load path
    # doesn't import or call the online LLM until a clinician requests
    # a patient summary by clicking on the patient.
    from app.agents.reasoning_agent import ReasoningAgent

    reasoning_agent = ReasoningAgent()
    summary = reasoning_agent.summarize(context, findings)

    risk_level = _risk_from_findings(findings)

    return PatientSummaryOut(
        patient_id=patient_id,
        risk_level=risk_level,
        alerts=[alert["message"] for alert in alerts] if alerts else [f["message"] for f in findings],
        summary=summary,
        context=context,
    )


@router.get("/dashboard/clinician", response_model=list[ClinicianPatientCard])
def get_clinician_dashboard(db: Session = Depends(get_db)):
    # Only fetch hypertension conditions (SQL-filtered via expression index)
    all_conditions = list_hypertension_condition_rows(db)
    if not all_conditions:
        return []

    conditions_by_patient: dict[str, list[dict]] = defaultdict(list)
    hyp_patient_ids: set[str] = set()
    for condition in all_conditions:
        pid = condition.get("patient_id")
        if pid:
            conditions_by_patient[pid].append(condition)
            hyp_patient_ids.add(pid)

    # Only load the ~500 hypertension patients, not all 2k+
    patients = get_patient_rows_for_ids(db, hyp_patient_ids)

    # One row per patient: latest BP only — avoids shipping 13k full JSONB rows
    latest_bp_rows = list_latest_bp_per_patient(db, hyp_patient_ids)
    observations_by_patient: dict[str, list[dict]] = defaultdict(list)
    for obs in latest_bp_rows:
        pid = obs.get("patient_id")
        if pid:
            observations_by_patient[pid].append(obs)

    all_alerts = alert_service.list_alerts(db)
    alerts_by_patient: dict[str, list[dict]] = defaultdict(list)
    for alert in all_alerts:
        pid = alert.get("patient_resource_id")
        if pid and pid in hyp_patient_ids:
            alerts_by_patient[pid].append(alert)

    cards: list[ClinicianPatientCard] = []
    for patient in patients:
        pid = patient["patient_id"]
        conditions = conditions_by_patient.get(pid, [])
        observations = observations_by_patient.get(pid, [])
        context = context_service.build_context_from_records(pid, conditions, observations)
        alerts = alerts_by_patient.get(pid, [])
        findings = monitoring_agent.evaluate(observations)
        cards.append(
            ClinicianPatientCard(
                patient_id=pid,
                full_name=patient["full_name"],
                risk_level=_risk_from_findings(findings),
                last_bp=context["context"]["last_bp"],
                alerts=[a["message"] for a in alerts] if alerts else [f["message"] for f in findings],
            )
        )
    return cards


@router.get("/{patient_id}/bp-trend", response_model=list[BPTrendPoint])
def get_patient_bp_trend(patient_id: str, db: Session = Depends(get_db)):
    patient = get_patient_row(db, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail="Patient not found")

    observations = observations_for_patient(db, patient_id)
    readings_by_date = {reading["observed_on"]: reading for reading in observations}
    points: list[BPTrendPoint] = []
    for observed_on in sorted(readings_by_date):
        reading = readings_by_date[observed_on]
        points.append(
            BPTrendPoint(
                observed_on=observed_on,
                systolic=reading["systolic"],
                diastolic=reading["diastolic"],
            )
        )

    return points[-20:]
