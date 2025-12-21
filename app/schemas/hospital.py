from sqlmodel import SQLModel, Field
from datetime import date, datetime
from typing import List, Optional
from pydantic import FieldValidationInfo, field_validator, model_validator

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


class NurseTaskMedicineItem(SQLModel):
    medicine_id: int
    name: Optional[str] = None
    quantity: int = Field(gt=0)
    usage: str


class NurseTaskPlan(SQLModel):
    type: str
    start_time: datetime
    duration_days: int = Field(default=1, ge=1, le=30)
    times_per_day: Optional[int] = Field(default=None, ge=1, le=6)
    interval_days: Optional[int] = Field(default=None, ge=1, le=30)
    detail: Optional[str] = None
    medicines: List[NurseTaskMedicineItem] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_plan(cls, values: "NurseTaskPlan") -> "NurseTaskPlan":
        medication_types = {"输液", "吃药"}
        detail_types = {"针灸", "手术"}

        if values.times_per_day and values.interval_days:
            raise ValueError("不能同时设置每天次数与间隔天数")
        if not values.times_per_day and not values.interval_days:
            values.times_per_day = 1

        if values.type in medication_types and not values.medicines:
            raise ValueError("药品类任务需至少选择一种药品")
        if values.type in detail_types and not (values.detail and values.detail.strip()):
            raise ValueError("请填写该项目的详细说明")

        return values


class NurseTaskBatchCreate(SQLModel):
    plans: List[NurseTaskPlan]


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
    ward_id: int
    dept_id: int
    type: str
    bed_count: int

    @field_validator("ward_id")
    @classmethod
    def validate_ward_id(cls, value: int) -> int:
        if value < 101 or value > 999:
            raise ValueError("房间号需在 101-999 之间")
        return value

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