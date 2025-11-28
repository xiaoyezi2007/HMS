from sqlmodel import SQLModel
from datetime import date, datetime
from pydantic import field_validator

from app.models.hospital import Gender, RegType

# --- 患者完善信息用 ---
class PatientCreate(SQLModel):
    name: str
    gender: Gender
    birth_date: date
    id_number: str
    address: str

# --- 挂号动作 ---
class RegistrationCreate(SQLModel):
    doctor_id: int
    reg_type: RegType = RegType.NORMAL

# --- 医生写病历 ---
class MedicalRecordCreate(SQLModel):
    complaint: str
    diagnosis: str
    suggestion: str = None


class ExaminationCreate(SQLModel):
    type: str


class ExaminationRead(SQLModel):
    exam_id: int
    type: str
    result: str
    date: datetime
    record_id: int


class PaymentCreate(SQLModel):
    type: str
    amount: float
    patient_id: int
    pres_id: int | None = None
    exam_id: int | None = None
    hosp_id: int | None = None
    status: str | None = None


class PaymentRead(SQLModel):
    payment_id: int
    type: str
    amount: float
    time: datetime
    patient_id: int
    pres_id: int | None = None
    exam_id: int | None = None
    hosp_id: int | None = None
    status: str


ALLOWED_DOCTOR_TITLES = {"主治医师", "普通医师"}


class DoctorTitleUpdate(SQLModel):
    title: str

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        if value not in ALLOWED_DOCTOR_TITLES:
            raise ValueError("医生职称仅支持主治医师或普通医师")
        return value


class NurseHeadUpdate(SQLModel):
    is_head_nurse: bool