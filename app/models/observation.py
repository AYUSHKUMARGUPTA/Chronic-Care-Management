from datetime import date

from sqlalchemy import Date, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Observation(Base):
    __tablename__ = "fhir_observation"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("fhir_patient.id"), index=True)
    obs_type: Mapped[str] = mapped_column(String(32), index=True)  # systolic / diastolic
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str | None] = mapped_column(String(32), nullable=True)
    observed_on: Mapped[date] = mapped_column(Date, index=True)
