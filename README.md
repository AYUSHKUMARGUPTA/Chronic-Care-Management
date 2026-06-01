# Hypertension Vertical Slice (FastAPI + PostgreSQL)

This project is a production-style capstone MVP focused on one use case:
**hypertension care-gap detection**.

## What is implemented

- FHIR-like ingestion endpoint (synthetic payload support)
- Three agents:
  - Ingestion agent
  - Monitoring agent
  - Reasoning agent
- Core APIs:
  - `GET /patients`
  - `GET /patients/{id}/summary`
  - `GET /patients/dashboard/clinician`
  - `GET /alerts`
- PostgreSQL persistence via SQLAlchemy

## Quick start

1. Ensure PostgreSQL is running and create a database.
2. Create environment file:

```bash
cp .env.example .env
```

3. Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

4. Run app:

```bash
uvicorn app.main:app --reload
```

5. Open docs:

- http://127.0.0.1:8000/docs

## Import Synthea data (optional)

Bulk import reads **[Synthea](https://github.com/synthetichealth/synthea)** data in **FHIR R4 bulk NDJSON** (one JSON resource per line in each file). **You do not need Synthea for a normal demo**—use `scripts/seed_sample.py` or **Load Demo Patient** in the dashboard instead.

### If you do not have Synthea exports yet

```bash
python scripts/seed_sample.py
```

Or with the API running: **Load Demo Patient** in the clinician dashboard (`POST /ingestion/demo-seed`).

---

### Import real Synthea bulk data (step by step)

#### 1. Prerequisites on your machine

- **Java JDK 17+** (Synthea requirement; see [Synthea README](https://github.com/synthetichealth/synthea/blob/master/README.md)).
- This repo: **PostgreSQL running**, `.env` configured, and `pip install -e .` (see Quick start).

#### 2. Install and build Synthea (once)

```bash
git clone https://github.com/synthetichealth/synthea.git
cd synthea
./gradlew build check test
```

(Follow [Basic Setup and Running](https://github.com/synthetichealth/synthea/wiki/Basic-Setup-and-Running) if you prefer a lighter path than a full test run.)

#### 3. Turn on bulk FHIR (NDJSON) export

Synthea’s default FHIR output is **per-patient JSON bundles**, which this importer does **not** read. You need **bulk NDJSON** so that `Patient.ndjson`, `Condition.ndjson`, `MedicationRequest.ndjson`, and `Observation.ndjson` exist under `output/fhir/`.

**Option A — no file edits (recommended):** pass the property on the command line (any `synthea.properties` key works as `--key=value`; see Synthea `-h`):

```bash
cd synthea   # your Synthea clone
./run_synthea -p 2000 --exporter.fhir.bulk_data=true
```

**Option B — edit config:** in `synthea/src/main/resources/synthea.properties`, set `exporter.fhir.bulk_data = true` (and keep `exporter.fhir.export = true`), then run `./run_synthea -p 2000`. Details: [Synthea wiki — HL7 FHIR](https://github.com/synthetichealth/synthea/wiki/HL7-FHIR).

`-p` is population size; increase it if you want more candidates (hypertension is common but not universal).

#### 4. Confirm the four NDJSON files exist

After the run finishes, check Synthea’s output tree (by default next to the clone):

```text
synthea/output/fhir/Patient.ndjson
synthea/output/fhir/Condition.ndjson
synthea/output/fhir/MedicationRequest.ndjson
synthea/output/fhir/Observation.ndjson
```

If you used `--exporter.baseDirectory=...`, look under that directory instead.

#### 5. Run this project’s importer

From the **Capstone** repo root (not `synthea/`), with your venv activated:

```bash
cd /path/to/Capstone
source .venv/bin/activate
python scripts/import_synthea.py \
  --patients /path/to/synthea/output/fhir/Patient.ndjson \
  --conditions /path/to/synthea/output/fhir/Condition.ndjson \
  --medications /path/to/synthea/output/fhir/MedicationRequest.ndjson \
  --observations /path/to/synthea/output/fhir/Observation.ndjson \
  --limit 1000
```

Replace `/path/to/synthea` with the absolute path to your Synthea clone. **`\\` must be the last character on each continued line** (no spaces after `\`), or paste a single line:

```bash
python scripts/import_synthea.py --patients /ABS/PATH/synthea/output/fhir/Patient.ndjson --conditions /ABS/PATH/synthea/output/fhir/Condition.ndjson --medications /ABS/PATH/synthea/output/fhir/MedicationRequest.ndjson --observations /ABS/PATH/synthea/output/fhir/Observation.ndjson --limit 1000
```

`--limit` caps how many **hypertensive** patients are ingested (see below), not how many lines Synthea wrote.

#### 6. What actually gets imported

The script only creates patients who have a **hypertension-related** `Condition` (SNOMED `38341003` / `59621000`, or display text containing `hypertens`). It attaches their `MedicationRequest` and blood-pressure `Observation` rows when present (BP panel LOINC `55284-4` with systolic/diastolic components). Patients without that condition are skipped.

#### 7. Verify

- Importer prints how many patients were imported and total count in the DB.
- Open `http://127.0.0.1:8000/docs` and call `GET /patients` or use the React dashboard.

#### Troubleshooting

| Symptom | What to check |
|--------|----------------|
| No `*.ndjson` under `output/fhir/`, only many small `.json` files | Bulk mode is off; rerun Synthea with `--exporter.fhir.bulk_data=true` (or set it in `synthea.properties`). |
| Importer imports `0` patients | Population may be too small, or few members have hypertension in the slice; increase `-p` or inspect `Condition.ndjson` for hypertension codes. |
| `FileNotFoundError` | Use real absolute paths to the four files; `/path/to/...` in docs is only an example. |

## Clinician dashboard (React)

```bash
cd web
npm install
npm run dev
```

The dashboard reads backend data from `http://127.0.0.1:8000` by default.
Set `VITE_API_BASE` if needed.
Click any patient row to open a detail panel backed by `GET /patients/{id}/summary`.
The detail panel also renders a mini BP trend chart using `GET /patients/{id}/bp-trend`.
Trend view includes guideline threshold overlays (140/90) and highlights above-threshold points.
Detail view also displays a trend status label (`Improving`, `Worsening`, `Stable`, `Insufficient Data`) using recent readings.
Use **Load Demo Patient** in the dashboard to insert demo-ready hypertensive data with one click (`POST /ingestion/demo-seed`).
Use **Reset Demo Data** to remove only seeded demo patients (`DELETE /ingestion/demo-seed`) between presentations.

## Suggested next steps

- Add migrations with Alembic
- Wire LLM for reasoning agent
- Add authentication and role-based access controls

## Evaluator demo script (3-5 minutes)

1. Start backend (`uvicorn app.main:app --reload`) and frontend (`cd web && npm run dev`).
2. Open dashboard and click **Load Demo Patient** 2-3 times.
3. Show risk distribution cards updating in real time.
4. Click a patient row and walk through:
   - reasoning summary
   - active alerts
   - BP trend chart with 140/90 overlays
   - trend status label
5. Click **Reset Demo Data** to show safe demo-state cleanup.
