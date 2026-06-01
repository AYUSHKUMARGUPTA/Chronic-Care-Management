from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from app.api.routes import alerts, ingestion, patients
from app.api import websocket as websocket_router
from app.db.session import engine

app = FastAPI(title="Hypertension Care-Gap API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def on_startup() -> None:
    inspector = inspect(engine)
    table_names = set(inspector.get_table_names())

    if "alerts" in table_names:
        existing_columns = {column["name"] for column in inspector.get_columns("alerts")}
        migration_statements: list[str] = []

        if "patient_resource_id" not in existing_columns:
            migration_statements.append("ALTER TABLE alerts ADD COLUMN patient_resource_id TEXT")
        if "status" not in existing_columns:
            migration_statements.append(
                "ALTER TABLE alerts ADD COLUMN status VARCHAR(24) NOT NULL DEFAULT 'PROVISIONAL'"
            )
        if "approved_by" not in existing_columns:
            migration_statements.append("ALTER TABLE alerts ADD COLUMN approved_by VARCHAR(64)")
        if "approved_at" not in existing_columns:
            migration_statements.append("ALTER TABLE alerts ADD COLUMN approved_at TIMESTAMP")
        if "created_at" not in existing_columns:
            migration_statements.append(
                "ALTER TABLE alerts ADD COLUMN created_at TIMESTAMP NOT NULL DEFAULT NOW()"
            )

        if migration_statements:
            with engine.begin() as connection:
                for statement in migration_statements:
                    connection.execute(text(statement))

    if "memories" not in table_names:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    CREATE TABLE IF NOT EXISTS memories (
                        id SERIAL PRIMARY KEY,
                        patient_resource_id TEXT NOT NULL,
                        snapshot JSON NOT NULL,
                        created_at TIMESTAMP NOT NULL DEFAULT NOW()
                    )
                    """
                )
            )


app.include_router(patients.router)
app.include_router(alerts.router)
app.include_router(ingestion.router)
app.include_router(websocket_router.router)
from app.api.routes import validation as validation_router
app.include_router(validation_router.router)
from app.tasks import background_monitor
# start periodic background monitor (interval seconds configurable via env later)
background_monitor.start_background_monitor(app, interval_seconds=60)


@app.get("/")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "hypertension-vertical-slice"}
