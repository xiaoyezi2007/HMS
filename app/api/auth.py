from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import get_session
from app.core.security import get_password_hash, verify_password, create_access_token
from app.models.user import UserAccount
from app.schemas.user import UserCreate, Token

router = APIRouter()


# --- 1. 用户注册接口 ---
@router.post("/register", response_model=UserAccount)
async def register(user_in: UserCreate, session: AsyncSession = Depends(get_session)):
    # A. 检查手机号是否已被注册
    result = await session.execute(select(UserAccount).where(UserAccount.phone == user_in.phone))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="该手机号已被注册")

    # B. 检查用户名是否已被占用
    result = await session.execute(select(UserAccount).where(UserAccount.username == user_in.username))
    if result.scalars().first():
        raise HTTPException(status_code=400, detail="该用户名已被占用")

    # C. 创建新用户
    new_user = UserAccount(
        phone=user_in.phone,
        username=user_in.username,
        role=user_in.role,
        password_hash=get_password_hash(user_in.password),  # 注意：这里存的是加密后的密码
        status="启用"
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)
    return new_user


# --- 2. 用户登录接口 ---
# OAuth2PasswordRequestForm 是 FastAPI 自带的表单处理，它要求前端传 'username' 和 'password'
# 注意：虽然字段名是 username，但我们逻辑里用 phone 来匹配
@router.post("/login", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_session)):
    # A. 根据手机号查询用户 (form_data.username 对应前端传来的手机号)
    result = await session.execute(select(UserAccount).where(UserAccount.phone == form_data.username))
    user = result.scalars().first()

    # B. 验证用户是否存在以及密码是否正确
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="手机号或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # C. 生成 Token
    access_token = create_access_token(data={"sub": user.phone, "role": user.role.value})

    return {"access_token": access_token, "token_type": "bearer"}