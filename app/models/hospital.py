from sqlmodel import SQLModel, Field, Relationship
from datetime import date, datetime
from typing import Optional, List
from enum import Enum


# --- 枚举类型 ---
class Gender(str, Enum):
    MALE = "男"
    FEMALE = "女"


class RegStatus(str, Enum):
    WAITING = "待就诊"
    COMPLETED = "已就诊"
    CANCELLED = "已取消"


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
    title: str = Field(max_length=50, description="职称：主任医师/副主任医师")
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
    reg_date: datetime = Field(default_factory=datetime.now)
    reg_type: RegType = Field(default=RegType.NORMAL)
    fee: float = Field(default=0.0)
    status: RegStatus = Field(default=RegStatus.WAITING)

    # 外键
    patient_id: int = Field(foreign_key="patient.patient_id")
    doctor_id: int = Field(foreign_key="doctor.doctor_id")