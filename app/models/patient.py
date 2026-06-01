from sqlalchemy import Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class Patient(Base):
    __tablename__ = "fhir_patient"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    birth_date: Mapped[Date | None] = mapped_column(Date, nullable=True)
    gender: Mapped[str | None] = mapped_column(String(32), nullable=True)

class Condition(Base):
    __tablename__ = "fhir_conditions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("fhir_patient.id"), index=True)
    code: Mapped[str] = mapped_column(String(64), index=True)
    display: Mapped[str] = mapped_column(String(255))
    clinical_status: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Medication(Base):
    __tablename__ = "fhir_medications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("fhir_patient.id"), index=True)
    code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    display: Mapped[str] = mapped_column(String(255))
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)
