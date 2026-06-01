import argparse
import json
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.agents.ingestion_agent import IngestionAgent
from app.db.session import SessionLocal
from app.models.patient import Patient
from app.schemas.ingestion import (
    FhirBundleIn,
    FhirConditionIn,
    FhirMedicationIn,
    FhirObservationIn,
    FhirPatientIn,
)

BP_PANEL = "55284-4"
SYSTOLIC = "8480-6"
DIASTOLIC = "8462-4"
HYPERTENSION_CODES = {"38341003", "59621000"}


def _load_json_flexible(path: Path) -> list[dict[str, Any]]:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        return []

    if raw.startswith("["):
        data = json.loads(raw)
        return data if isinstance(data, list) else []

    records: list[dict[str, Any]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        records.append(json.loads(line))
    return records


def _patient_name(resource: dict[str, Any]) -> str:
    names = resource.get("name", [])
    if not names:
        return "Unknown"
    first = names[0]
    given = " ".join(first.get("given", []))
    family = first.get("family", "")
    full = f"{given} {family}".strip()
    return full or "Unknown"


def _patient_ref_id(resource: dict[str, Any]) -> str | None:
    ref = resource.get("subject", {}).get("reference")
    if not ref or "/" not in ref:
        return None
    return ref.split("/", 1)[1]


def _extract_observation(resource: dict[str, Any]) -> tuple[str, float, float] | None:
    code = resource.get("code", {})
    coding = code.get("coding", [])
    has_panel = any(c.get("code") == BP_PANEL for c in coding)
    if not has_panel:
        return None

    observed_on = resource.get("effectiveDateTime", "")
    if not observed_on:
        return None
    obs_date = observed_on[:10]

    systolic = None
    diastolic = None
    for comp in resource.get("component", []):
        comp_codes = comp.get("code", {}).get("coding", [])
        value = comp.get("valueQuantity", {}).get("value")
        for c in comp_codes:
            if c.get("code") == SYSTOLIC:
                systolic = value
            elif c.get("code") == DIASTOLIC:
                diastolic = value

    if systolic is None or diastolic is None:
        return None

    return obs_date, float(systolic), float(diastolic)


def import_synthea(
    db: Session,
    patients_path: Path,
    conditions_path: Path,
    medications_path: Path,
    observations_path: Path,
    limit: int | None,
) -> tuple[int, int]:
    ingestion = IngestionAgent()

    patients = _load_json_flexible(patients_path)
    conditions = _load_json_flexible(conditions_path)
    meds = _load_json_flexible(medications_path)
    observations = _load_json_flexible(observations_path)

    conditions_by_patient: dict[str, list[FhirConditionIn]] = defaultdict(list)
    meds_by_patient: dict[str, list[FhirMedicationIn]] = defaultdict(list)
    obs_by_patient: dict[str, list[FhirObservationIn]] = defaultdict(list)

    for resource in conditions:
        patient_id = _patient_ref_id(resource)
        if not patient_id:
            continue

        coding = resource.get("code", {}).get("coding", [])
        if not coding:
            continue

        code = str(coding[0].get("code", ""))
        display = str(coding[0].get("display", ""))
        if code not in HYPERTENSION_CODES and "hypertens" not in display.lower():
            continue

        clinical = resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code")
        conditions_by_patient[patient_id].append(
            FhirConditionIn(code=code, display=display or "Hypertension", clinical_status=clinical)
        )

    for resource in meds:
        patient_id = _patient_ref_id(resource)
        if not patient_id:
            continue

        med = resource.get("medicationCodeableConcept", {}).get("coding", [{}])[0]
        display = med.get("display") or resource.get("medicationCodeableConcept", {}).get("text")
        if not display:
            continue
        status = resource.get("status")
        meds_by_patient[patient_id].append(
            FhirMedicationIn(code=str(med.get("code", "")) or None, display=str(display), status=status)
        )

    temp_obs_by_patient: dict[str, dict[str, tuple[float, float]]] = defaultdict(dict)
    for resource in observations:
        patient_id = _patient_ref_id(resource)
        if not patient_id:
            continue

        parsed = _extract_observation(resource)
        if not parsed:
            continue

        obs_date, systolic, diastolic = parsed
        temp_obs_by_patient[patient_id][obs_date] = (systolic, diastolic)

    for patient_id, records in temp_obs_by_patient.items():
        for obs_date, (sys_val, dia_val) in records.items():
            obs_by_patient[patient_id].append(
                FhirObservationIn(
                    systolic=sys_val,
                    diastolic=dia_val,
                    observed_on=date.fromisoformat(obs_date),
                )
            )

    imported = 0
    for resource in patients:
        pid = resource.get("id")
        if not pid:
            continue
        if pid not in conditions_by_patient:
            continue

        bundle = FhirBundleIn(
            patient=FhirPatientIn(
                external_id=str(pid),
                full_name=_patient_name(resource),
                birth_date=(
                    date.fromisoformat(resource["birthDate"])
                    if resource.get("birthDate")
                    else None
                ),
                gender=resource.get("gender"),
            ),
            conditions=conditions_by_patient.get(pid, []),
            medications=meds_by_patient.get(pid, []),
            observations=obs_by_patient.get(pid, []),
        )

        ingestion.ingest_bundle(db, bundle, commit=False)
        imported += 1
        if limit and imported >= limit:
            break

    db.commit()
    total_patients = db.scalar(select(func.count(Patient.id)))
    return imported, total_patients or 0


def main() -> None:
    # Drop stray argv tokens (often from pasted line continuations like `\ ` mid-line).
    sys.argv = [a for a in sys.argv if a.strip()]

    parser = argparse.ArgumentParser(description="Import Synthea FHIR JSON into MVP schema.")
    parser.add_argument("--patients", required=True, help="Path to Patient.ndjson/json")
    parser.add_argument("--conditions", required=True, help="Path to Condition.ndjson/json")
    parser.add_argument("--medications", required=True, help="Path to MedicationRequest.ndjson/json")
    parser.add_argument("--observations", required=True, help="Path to Observation.ndjson/json")
    parser.add_argument("--limit", type=int, default=None, help="Optional patient import limit")
    args = parser.parse_args()

    inputs = {
        "patients": Path(args.patients),
        "conditions": Path(args.conditions),
        "medications": Path(args.medications),
        "observations": Path(args.observations),
    }
    missing = [(name, p.expanduser()) for name, p in inputs.items() if not p.expanduser().is_file()]
    if missing:
        bullet = "\n".join(f"  --{label}: {path}" for label, path in missing)
        parser.error(
            "expected existing files (your Synthea NDJSON exports), got:\n"
            f"{bullet}\n\n"
            "README uses /path/to/... only as placeholders. Point each flag at a real "
            "file path (e.g. .../output/Patient.ndjson from a Synthea run)."
        )

    db = SessionLocal()
    try:
        imported, total = import_synthea(
            db=db,
            patients_path=Path(args.patients),
            conditions_path=Path(args.conditions),
            medications_path=Path(args.medications),
            observations_path=Path(args.observations),
            limit=args.limit,
        )
        print(f"Imported {imported} hypertensive patients. Total patients in DB: {total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
