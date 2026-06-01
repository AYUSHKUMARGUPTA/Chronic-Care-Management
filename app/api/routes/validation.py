from datetime import datetime

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.alert import Alert

router = APIRouter(prefix="/validation", tags=["validation"])


@router.post("/{alert_id}/approve")
def approve_alert(alert_id: int, approver: str = Body(..., embed=True), db: Session = Depends(get_db)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.status == "CONFIRMED":
        return {"status": "already_confirmed"}

    alert.status = "CONFIRMED"
    alert.approved_by = approver
    alert.approved_at = datetime.utcnow()
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return {"status": "confirmed", "alert_id": alert.id}


@router.post("/{alert_id}/reject")
def reject_alert(alert_id: int, approver: str = Body(..., embed=True), db: Session = Depends(get_db)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    if alert.status == "REJECTED":
        return {"status": "already_rejected"}

    alert.status = "REJECTED"
    alert.approved_by = approver
    alert.approved_at = datetime.utcnow()
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return {"status": "rejected", "alert_id": alert.id}
