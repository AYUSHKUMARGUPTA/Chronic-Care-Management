from __future__ import annotations

from collections import defaultdict
from datetime import date
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

HYPERTENSION_CODES = {"38341003", "59621000"}
BP_PANEL_CODE = "85354-9"
SYSTOLIC_CODE = "8480-6"
DIASTOLIC_CODE = "8462-4"


def _row_data(row: dict[str, Any]) -> dict[str, Any]:
    data = row.get("data")
    return data if isinstance(data, dict) else {}


def _patient_reference(patient_resource_id: str) -> str:
    return f"Patient/{patient_resource_id}"


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _format_patient_name(name_entry: dict[str, Any]) -> str | None:
    if not name_entry:
        return None

    parts: list[str] = []
    prefix = name_entry.get("prefix")
    given = name_entry.get("given")
    family = name_entry.get("family")
    suffix = name_entry.get("suffix")

    if isinstance(prefix, list):
        parts.extend(str(item).strip() for item in prefix if str(item).strip())
    if isinstance(given, list):
        parts.extend(str(item).strip() for item in given if str(item).strip())
    elif isinstance(given, str) and given.strip():
        parts.append(given.strip())
    if isinstance(family, str) and family.strip():
        parts.append(family.strip())
    if isinstance(suffix, list):
        parts.extend(str(item).strip() for item in suffix if str(item).strip())

    formatted = " ".join(parts).strip()
    return formatted or None


def parse_patient_row(row: dict[str, Any]) -> dict[str, Any]:
    data = _row_data(row)
    name_entries = data.get("name")
    first_name = name_entries[0] if isinstance(name_entries, list) and name_entries else {}
    full_name = None
    if isinstance(first_name, dict):
        full_name = first_name.get("text") if isinstance(first_name.get("text"), str) else None
        if not full_name:
            full_name = _format_patient_name(first_name)
    if not full_name:
        full_name = "Unknown"

    return {
        "patient_id": row.get("resource_id") or data.get("id"),
        "full_name": full_name,
        "birth_date": _parse_date(data.get("birthDate")),
        "gender": data.get("gender"),
        "raw": data,
    }


def parse_condition_row(row: dict[str, Any]) -> dict[str, Any]:
    data = _row_data(row)
    coding = (data.get("code") or {}).get("coding") or []
    first_code = coding[0] if coding and isinstance(coding[0], dict) else {}
    clinical_status = ((data.get("clinicalStatus") or {}).get("coding") or [{}])[0].get("code")
    subject_ref = ((data.get("subject") or {}).get("reference"))
    patient_id = subject_ref.split("/", 1)[1] if isinstance(subject_ref, str) and "/" in subject_ref else None
    return {
        "patient_id": patient_id,
        "code": str(first_code.get("code", "")),
        "display": str(first_code.get("display") or (data.get("code") or {}).get("text") or ""),
        "clinical_status": clinical_status,
        "raw": data,
    }


def parse_medication_row(row: dict[str, Any]) -> dict[str, Any]:
    data = _row_data(row)
    med_concept = data.get("medicationCodeableConcept") or {}
    coding = med_concept.get("coding") or []
    first_code = coding[0] if coding and isinstance(coding[0], dict) else {}
    subject_ref = (data.get("subject") or {}).get("reference")
    patient_id = subject_ref.split("/", 1)[1] if isinstance(subject_ref, str) and "/" in subject_ref else None
    return {
        "patient_id": patient_id,
        "code": str(first_code.get("code", "")) or None,
        "display": str(first_code.get("display") or med_concept.get("text") or "Unknown medication"),
        "status": data.get("status"),
        "raw": data,
    }


def parse_observation_row(row: dict[str, Any]) -> dict[str, Any] | None:
    data = _row_data(row)
    code_entries = ((data.get("code") or {}).get("coding") or [])
    if not any(isinstance(entry, dict) and entry.get("code") == BP_PANEL_CODE for entry in code_entries):
        return None

    effective = data.get("effectiveDateTime") or data.get("effectiveInstant")
    if not isinstance(effective, str) or not effective:
        return None

    systolic = None
    diastolic = None
    for component in data.get("component") or []:
        if not isinstance(component, dict):
            continue
        component_codes = ((component.get("code") or {}).get("coding") or [])
        value = (component.get("valueQuantity") or {}).get("value")
        for entry in component_codes:
            if not isinstance(entry, dict):
                continue
            if entry.get("code") == SYSTOLIC_CODE:
                systolic = value
            elif entry.get("code") == DIASTOLIC_CODE:
                diastolic = value

    if systolic is None or diastolic is None:
        return None

    subject_ref = (data.get("subject") or {}).get("reference")
    patient_id = subject_ref.split("/", 1)[1] if isinstance(subject_ref, str) and "/" in subject_ref else None
    if not patient_id:
        return None

    return {
        "patient_id": patient_id,
        "observed_on": effective[:10],
        "systolic": float(systolic),
        "diastolic": float(diastolic),
        "raw": data,
    }


def list_patient_rows(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        text("SELECT resource_id, data, _ingested_at FROM fhir_patient ORDER BY _ingested_at, resource_id")
    ).mappings().all()
    return [parse_patient_row(dict(row)) for row in rows]


def list_condition_rows(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(text("SELECT resource_id, data FROM fhir_condition")).mappings().all()
    return [parse_condition_row(dict(row)) for row in rows]


def list_medication_rows(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(text("SELECT resource_id, data FROM fhir_medicationrequest")).mappings().all()
    return [parse_medication_row(dict(row)) for row in rows]


def list_observation_rows(db: Session) -> list[dict[str, Any]]:
    rows = db.execute(
        text(
            "SELECT resource_id, data FROM fhir_observation"
            f" WHERE data->'code'->'coding'->0->>'code' = '{BP_PANEL_CODE}'"
        )
    ).mappings().all()
    readings: list[dict[str, Any]] = []
    for row in rows:
        parsed = parse_observation_row(dict(row))
        if parsed:
            readings.append(parsed)
    return readings


def list_hypertension_condition_rows(db: Session) -> list[dict[str, Any]]:
    """Return flat condition rows for hypertension patients only (no full JSONB transfer)."""
    rows = db.execute(
        text("""
            SELECT
                data->'subject'->>'reference'                        AS patient_ref,
                data->'code'->'coding'->0->>'code'                   AS code,
                COALESCE(
                    data->'code'->'coding'->0->>'display',
                    data->'code'->>'text'
                )                                                    AS display,
                data->'clinicalStatus'->'coding'->0->>'code'         AS clinical_status
            FROM fhir_condition
            WHERE data->'code'->'coding'->0->>'code' = ANY(:codes)
        """),
        {"codes": list(HYPERTENSION_CODES)},
    ).mappings().all()
    result: list[dict[str, Any]] = []
    for row in rows:
        ref = row["patient_ref"]
        pid = ref.split("/", 1)[1] if isinstance(ref, str) and "/" in ref else None
        if pid:
            result.append({
                "patient_id": pid,
                "code": row["code"] or "",
                "display": row["display"] or "",
                "clinical_status": row["clinical_status"],
            })
    return result


def list_medications_for_patient_ids(db: Session, patient_ids: set[str]) -> list[dict[str, Any]]:
    if not patient_ids:
        return []
    refs = [f"Patient/{pid}" for pid in patient_ids]
    rows = db.execute(
        text("""
            SELECT resource_id, data
            FROM fhir_medicationrequest
            WHERE data->'subject'->>'reference' = ANY(:refs)
            ORDER BY resource_id
        """),
        {"refs": refs},
    ).mappings().all()
    return [parse_medication_row(dict(row)) for row in rows]


def get_patient_rows_for_ids(db: Session, patient_ids: set[str]) -> list[dict[str, Any]]:
    if not patient_ids:
        return []
    rows = db.execute(
        text(
            "SELECT resource_id, data, _ingested_at FROM fhir_patient"
            " WHERE resource_id = ANY(:ids) ORDER BY resource_id"
        ),
        {"ids": list(patient_ids)},
    ).mappings().all()
    return [parse_patient_row(dict(row)) for row in rows]


def list_latest_bp_per_patient(
    db: Session, patient_ids: set[str]
) -> list[dict[str, Any]]:
    """Return up to the 3 most recent BP readings per patient.

    3 readings are needed for the BP trend check in MonitoringAgent; returning
    only 1 caused the dashboard and detail view to disagree on risk level.
    mv_bp_readings holds pre-extracted values so this never touches the JSONB heap.
    """
    if not patient_ids:
        return []
    refs = [f"Patient/{pid}" for pid in patient_ids]
    rows = db.execute(
        text("""
            SELECT patient_ref, observed_on, systolic, diastolic
            FROM (
                SELECT
                    patient_ref, observed_on, systolic, diastolic,
                    ROW_NUMBER() OVER (
                        PARTITION BY patient_ref
                        ORDER BY observed_on DESC NULLS LAST
                    ) AS rn
                FROM mv_bp_readings
                WHERE patient_ref = ANY(:refs)
                  AND systolic IS NOT NULL
                  AND diastolic IS NOT NULL
            ) ranked
            WHERE rn <= 3
            ORDER BY patient_ref, observed_on
        """),
        {"refs": refs},
    ).mappings().all()
    result: list[dict[str, Any]] = []
    for row in rows:
        ref = row["patient_ref"]
        pid = ref.split("/", 1)[1] if isinstance(ref, str) and "/" in ref else None
        if pid:
            result.append({
                "patient_id": pid,
                "observed_on": str(row["observed_on"]),
                "systolic": float(row["systolic"]),
                "diastolic": float(row["diastolic"]),
            })
    return result


def get_patient_row(db: Session, patient_id: str) -> dict[str, Any] | None:
    row = db.execute(
        text("SELECT resource_id, data, _ingested_at FROM fhir_patient WHERE resource_id = :patient_id"),
        {"patient_id": patient_id},
    ).mappings().first()
    return parse_patient_row(dict(row)) if row else None


def conditions_for_patient(db: Session, patient_id: str) -> list[dict[str, Any]]:
    reference = _patient_reference(patient_id)
    rows = db.execute(
        text("""
            SELECT resource_id, data
            FROM fhir_condition
            WHERE data->'subject'->>'reference' = :reference
            ORDER BY resource_id
        """),
        {"reference": reference},
    ).mappings().all()
    return [parse_condition_row(dict(row)) for row in rows]


def medications_for_patient(db: Session, patient_id: str) -> list[dict[str, Any]]:
    reference = _patient_reference(patient_id)
    rows = db.execute(
        text("""
            SELECT resource_id, data
            FROM fhir_medicationrequest
            WHERE data->'subject'->>'reference' = :reference
            ORDER BY resource_id
        """),
        {"reference": reference},
    ).mappings().all()
    return [parse_medication_row(dict(row)) for row in rows]


def observations_for_patient(db: Session, patient_id: str) -> list[dict[str, Any]]:
    reference = _patient_reference(patient_id)
    rows = db.execute(
        text("""
            SELECT patient_ref, observed_on, systolic, diastolic
            FROM mv_bp_readings
            WHERE patient_ref = :reference
              AND systolic IS NOT NULL
              AND diastolic IS NOT NULL
            ORDER BY observed_on
        """),
        {"reference": reference},
    ).mappings().all()
    return [
        {
            "patient_id": patient_id,
            "observed_on": str(row["observed_on"]),
            "systolic": float(row["systolic"]),
            "diastolic": float(row["diastolic"]),
        }
        for row in rows
    ]


def patient_has_hypertension(conditions: list[dict[str, Any]]) -> bool:
    for condition in conditions:
        code = condition.get("code", "")
        display = str(condition.get("display", "")).lower()
        if code in HYPERTENSION_CODES or "hypertens" in display:
            return True
    return False


def extract_latest_bp(readings: list[dict[str, Any]]) -> tuple[str, dict[str, Any] | None, dict[str, Any] | None]:
    if not readings:
        return "unknown", None, None

    ordered = sorted(readings, key=lambda item: item["observed_on"])
    latest = ordered[-1]
    return f"{int(latest['systolic'])}/{int(latest['diastolic'])}", latest, latest


def group_readings_by_patient(readings: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for reading in readings:
        patient_id = reading.get("patient_id")
        if patient_id:
            grouped[str(patient_id)].append(reading)
    return grouped
