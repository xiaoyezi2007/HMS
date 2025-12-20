from sqlmodel import SQLModel
from datetime import date, datetime
from pydantic import FieldValidationInfo, field_validator

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
    visit_date: date = date.today()

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


ALLOWED_DOCTOR_TITLES = {"专家医师", "普通医师", "主治医师"}

# --- 病房类型映射 ---
WARD_TYPE_RULES = {
    "单人房": 1,
    "双人房": 2,
    "四人病房": 4,
    "重症监护": 1
}


class DoctorTitleUpdate(SQLModel):
    title: str

    @field_validator("title")
    @classmethod
    def validate_title(cls, value: str) -> str:
        if value == "主治医师":
            value = "专家医师"
        if value not in ALLOWED_DOCTOR_TITLES:
            raise ValueError("医生级别仅支持专家医师或普通医师")
        return value


class NurseHeadUpdate(SQLModel):
    is_head_nurse: bool


class DepartmentCreate(SQLModel):
    dept_name: str
    telephone: str | None = None

    @field_validator("dept_name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("科室名称不能为空")
        return value.strip()


class WardCreate(SQLModel):
    dept_id: int
    type: str
    bed_count: int

    @field_validator("bed_count")
    @classmethod
    def validate_bed_count(cls, value: int, info: FieldValidationInfo) -> int:
        if value <= 0:
            raise ValueError("床位数必须大于 0")
        ward_type = info.data.get("type") if info and info.data else None
        if ward_type:
            expected = WARD_TYPE_RULES.get(ward_type)
            if expected is not None and value != expected:
                raise ValueError("床位数必须与病房类型保持一致")
        return value

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("病房类型不能为空")
        normalized = value.strip()
        if normalized not in WARD_TYPE_RULES:
            raise ValueError("病房类型仅能从预设列表选择")
        return normalized