from sqlmodel import SQLModel, Field, Relationship
from datetime import date, datetime
from typing import Optional, List
from enum import Enum
import random
from datetime import datetime as _datetime
from app.core.time_utils import now_bj, today_bj


# --- 枚举类型 ---
class Gender(str, Enum):
    MALE = "男"
    FEMALE = "女"


class RegStatus(str, Enum):
    WAITING = "排队中"
    IN_PROGRESS = "就诊中"
    FINISHED = "已完成"
    CANCELLED = "已取消"
    EXPIRED = "已过期"


class RegType(str, Enum):
    NORMAL = "普通号"
    EXPERT = "专家号"


# --- 1. 科室表 (Department) ---
class Department(SQLModel, table=True):
    dept_id: Optional[int] = Field(default=None, primary_key=True)
    dept_name: str = Field(max_length=100, unique=True)
    telephone: Optional[str] = Field(default=None, max_length=20)

    # 关系：一个科室有多个医生
    doctors: List["Doctor"] = Relationship(back_populates="department")


# --- 2. 医生表 (Doctor) ---
class Doctor(SQLModel, table=True):
    doctor_id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=50)
    gender: Gender
    title: str = Field(max_length=50, description="医生级别：专家医师/普通医师")
    phone: str = Field(max_length=11)

    # 外键：所属科室
    dept_id: Optional[int] = Field(default=None, foreign_key="department.dept_id")
    department: Optional[Department] = Relationship(back_populates="doctors")


# --- 3. 患者表 (Patient) ---
class Patient(SQLModel, table=True):
    patient_id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=50)
    gender: Gender
    birth_date: date
    id_number: str = Field(max_length=18, unique=True)
    address: Optional[str] = Field(default=None, max_length=200)

    # 核心关联：关联到 UserAccount 表的 phone
    # 这样我们就能通过登录的 Token 找到对应的 Patient 记录
    phone: str = Field(max_length=11, foreign_key="useraccount.phone", unique=True)


# --- 4. 挂号表 (Registration) ---
class Registration(SQLModel, table=True):
    reg_id: Optional[int] = Field(default=None, primary_key=True)
    reg_date: datetime = Field(default_factory=now_bj)
    visit_date: date = Field(default_factory=today_bj, description="就诊日期（具体到日）")
    reg_type: RegType = Field(default=RegType.NORMAL)
    fee: float = Field(default=0.0)
    status: RegStatus = Field(default=RegStatus.WAITING)
    symptoms: Optional[str] = Field(default=None, max_length=500, description="患者自述症状")

    # 外键
    patient_id: int = Field(foreign_key="patient.patient_id")
    doctor_id: int = Field(foreign_key="doctor.doctor_id")


# --- 5. 病历表 (MedicalRecord) ---
class MedicalRecord(SQLModel, table=True):
    record_id: Optional[int] = Field(default=None, primary_key=True)
    create_time: datetime = Field(default_factory=now_bj)

    # 核心字段 (PDF 1.4.6)
    complaint: str = Field(description="主诉")
    diagnosis: str = Field(description="诊断结果")
    suggestion: Optional[str] = Field(default=None, description="治疗建议")

    # 关联挂号单 (一对一)
    reg_id: int = Field(foreign_key="registration.reg_id", unique=True)
    # 关系：一个病历可以有多个检查记录
    exams: List["Examination"] = Relationship(back_populates="record")


# --- 9. 护士表 ---
class Nurse(SQLModel, table=True):
    nurse_id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=50)
    gender: Gender
    phone: str = Field(max_length=11, unique=True)
    is_head_nurse: bool = Field(default=False, description="是否为护士长")
    schedules: List["NurseSchedule"] = Relationship(back_populates="nurse")


# --- 10. 病房表 ---
class Ward(SQLModel, table=True):
    ward_id: Optional[int] = Field(default=None, primary_key=True)
    bed_count: int = Field(gt=0)
    type: str = Field(max_length=50)
    dept_id: int = Field(foreign_key="department.dept_id")
    schedules: List["NurseSchedule"] = Relationship(back_populates="ward")


# --- 11. 排班表 ---
class NurseSchedule(SQLModel, table=True):
    schedule_id: Optional[int] = Field(default=None, primary_key=True)
    nurse_id: int = Field(foreign_key="nurse.nurse_id")
    ward_id: int = Field(foreign_key="ward.ward_id")
    start_time: datetime = Field(description="值班开始时间")
    end_time: datetime = Field(description="值班结束时间")

    nurse: Optional[Nurse] = Relationship(back_populates="schedules")
    ward: Optional[Ward] = Relationship(back_populates="schedules")


# --- 11b. 护士代办表 (NurseTask) ---
class NurseTask(SQLModel, table=True):
    task_id: Optional[int] = Field(default=None, primary_key=True)
    type: str = Field(max_length=100, description="检查/任务类型")
    time: datetime = Field(description="需要完成的时间")
    status: str = Field(default="未完成", max_length=20, description="任务状态：未完成/已完成/已过期")
    hosp_id: int = Field(foreign_key="hospitalization.hosp_id")
    detail: Optional[str] = Field(default=None, description="任务详情/备注")
    medicine_snapshot: Optional[str] = Field(default=None, description="药品 + 用法 JSON 快照")
    service_fee: Optional[float] = Field(default=None, description="针灸/手术等额外服务费用")

    hospitalization: Optional["Hospitalization"] = Relationship()

# --- 12. 药品表 ---
class Medicine(SQLModel, table=True):
    medicine_id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(max_length=100, unique=True)
    price: float = Field(default=0.0)
    stock: int = Field(default=0)
    unit: str = Field(max_length=10)

# --- 13. 处方表 ---
class Prescription(SQLModel, table=True):
    pres_id: Optional[int] = Field(default=None, primary_key=True)
    record_id: int = Field(foreign_key="medicalrecord.record_id", unique=True)
    create_time: datetime = Field(default_factory=now_bj)
    total_amount: float = Field(default=0.0)
    details: List["PrescriptionDetail"] = Relationship(back_populates="prescription")

# --- 14. 处方明细 ---
class PrescriptionDetail(SQLModel, table=True):
    detail_id: Optional[int] = Field(default=None, primary_key=True)
    pres_id: int = Field(foreign_key="prescription.pres_id")
    medicine_id: int = Field(foreign_key="medicine.medicine_id")
    quantity: int = Field(gt=0)
    usage: str = Field(max_length=200)
    prescription: Optional[Prescription] = Relationship(back_populates="details")


# --- 15. 检查表 (Examination) ---
class ExamResult(str, Enum):
    VERY_LOW = "极低"
    LOW = "偏低"
    NORMAL = "正常"
    HIGH = "偏高"
    VERY_HIGH = "极高"


class Examination(SQLModel, table=True):
    exam_id: Optional[int] = Field(default=None, primary_key=True)
    type: str = Field(max_length=100, description="检查类型，由医生填写")
    result: str = Field(default=None, max_length=10, description="检查结果：极低/偏低/正常/偏高/极高")
    date: _datetime = Field(default_factory=now_bj)

    # 外键：关联病历（n:1）
    record_id: int = Field(foreign_key="medicalrecord.record_id")
    record: Optional[MedicalRecord] = Relationship(back_populates="exams")


# --- 16. 缴费表 (Payment) ---
class PaymentType(str, Enum):
    PRESCRIPTION = "处方费"
    EXAM = "检查费"
    HOSPITAL = "住院费"
    REGISTRATION = "挂号费"


class Payment(SQLModel, table=True):
    payment_id: Optional[int] = Field(default=None, primary_key=True)
    type: PaymentType
    amount: float = Field(default=0.0, ge=0)
    status: str = Field(default="未缴费")
    time: _datetime = Field(default_factory=now_bj)

    # 关联外键（可选）
    patient_id: int = Field(foreign_key="patient.patient_id")
    reg_id: Optional[int] = Field(default=None, foreign_key="registration.reg_id")
    pres_id: Optional[int] = Field(default=None, foreign_key="prescription.pres_id")
    exam_id: Optional[int] = Field(default=None, foreign_key="examination.exam_id")
    hosp_id: Optional[int] = Field(default=None, foreign_key="hospitalization.hosp_id")


# --- 16b. 住院表 (Hospitalization) ---
class Hospitalization(SQLModel, table=True):
    hosp_id: Optional[int] = Field(default=None, primary_key=True)
    status: str = Field(default="在院")
    in_date: datetime = Field(default_factory=now_bj)
    out_date: Optional[datetime] = Field(default=None)

    hosp_doctor_id: Optional[int] = Field(default=None, foreign_key="doctor.doctor_id")
    ward_id: Optional[int] = Field(default=None, foreign_key="ward.ward_id")
    record_id: Optional[int] = Field(default=None, foreign_key="medicalrecord.record_id")

    # 关系（可选）
    # record: Optional[MedicalRecord] = Relationship()