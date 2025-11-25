from sqlmodel import SQLModel
from app.models.user import UserRole

# 注册时，前端需要传这些数据
class UserCreate(SQLModel):
    phone: str
    username: str
    password: str
    role: UserRole = UserRole.PATIENT  # 默认为患者

# 登录成功后，后端返回的数据格式
class Token(SQLModel):
    access_token: str
    token_type: str