from sqlmodel import SQLModel
from datetime import date
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