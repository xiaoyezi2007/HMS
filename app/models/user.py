from sqlmodel import SQLModel, Field
from datetime import datetime
from typing import Optional

from app.core.time_utils import now_bj
from enum import Enum


# 定义角色枚举 (对应 PDF 中的 Role 字段)
class UserRole(str, Enum):
    PATIENT = "患者"
    DOCTOR = "医生"
    NURSE = "护士"
    PHARMACIST = "药师"
    ADMIN = "管理员"


# 定义数据库模型
class UserAccount(SQLModel, table=True):
    # 对应 PDF: Phone 手机号码 (主键)
    phone: str = Field(primary_key=True, max_length=11, description="手机号码，作为登录账号")

    # 对应 PDF: Username 用户名 (唯一，昵称)
    username: str = Field(max_length=50, unique=True, nullable=False)

    # 对应 PDF: PasswordHash (加密存储)
    password_hash: str = Field(max_length=255, nullable=False)

    # 对应 PDF: Role 用户角色
    role: UserRole = Field(nullable=False)

    # 对应 PDF: RegisterTime 注册时间
    register_time: datetime = Field(default_factory=datetime.now)

    # 对应 PDF: Status 账户状态 (启用/禁用)
    status: str = Field(default="启用", max_length=10)


class RegistrationAttempt(SQLModel, table=True):
    attempt_id: Optional[int] = Field(default=None, primary_key=True)
    ip_address: str = Field(max_length=45, index=True, description="请求来源 IP")
    created_at: datetime = Field(default_factory=now_bj)


class UserActionLog(SQLModel, table=True):
    log_id: Optional[int] = Field(default=None, primary_key=True)
    user_phone: str = Field(max_length=11, foreign_key="useraccount.phone", index=True)
    role: str = Field(max_length=20, description="用户角色快照")
    method: str = Field(max_length=10, description="HTTP 方法")
    path: str = Field(max_length=255, description="请求路径")
    action: str = Field(max_length=255, description="简要动作描述")
    status_code: int = Field(description="响应状态码")
    ip_address: str = Field(max_length=45, description="请求来源 IP")
    created_at: datetime = Field(default_factory=now_bj, description="发生时间")