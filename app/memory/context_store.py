from sqlalchemy.orm import Session

from app.models.memory import Memory


def save_memory(db: Session, patient_id: str, snapshot: dict) -> Memory:
    mem = Memory(patient_resource_id=patient_id, snapshot=snapshot)
    db.add(mem)
    db.commit()
    db.refresh(mem)
    return mem


def get_latest_memory(db: Session, patient_id: str) -> Memory | None:
    return (
        db.query(Memory)
        .filter(Memory.patient_resource_id == patient_id)
        .order_by(Memory.created_at.desc())
        .first()
    )
