from datetime import datetime
from sqlmodel import SQLModel
from pydantic import ConfigDict

from app.models.user import UserRole
from app.models.hospital import Gender

# 注册时，前端需要传这些数据
class UserCreate(SQLModel):
    phone: str
    username: str
    password: str
    role: UserRole = UserRole.PATIENT  # 默认为患者


class StaffAccountCreate(SQLModel):
    phone: str
    username: str
    role: UserRole
    dept_id: int | None = None
    doctor_name: str | None = None
    doctor_gender: Gender | None = None
    doctor_title: str | None = None
    nurse_name: str | None = None
    nurse_gender: Gender | None = None


class UserAccountSafe(SQLModel):
    phone: str
    username: str
    role: UserRole
    status: str
    register_time: datetime

    model_config = ConfigDict(from_attributes=True)


# 登录成功后，后端返回的数据格式
class Token(SQLModel):
    access_token: str
    token_type: str


class ChangePassword(SQLModel):
    current_password: str
    new_password: str