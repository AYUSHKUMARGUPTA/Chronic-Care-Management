from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.common import AlertOut
from app.services.alert_service import AlertService

router = APIRouter(prefix="/alerts", tags=["alerts"])
service = AlertService()


@router.get("", response_model=list[AlertOut])
def list_alerts(db: Session = Depends(get_db)):
    return service.list_alerts(db)


@router.post("/refresh/{patient_id}", response_model=list[AlertOut])
def refresh_alerts_for_patient(patient_id: str, db: Session = Depends(get_db)):
    return service.refresh_for_patient(db, patient_id)


@router.get("/patient/{patient_id}", response_model=list[AlertOut])
def list_alerts_for_patient(patient_id: str, db: Session = Depends(get_db)):
    return service.list_alerts_for_patient(db, patient_id)
