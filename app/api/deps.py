from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.security import SECRET_KEY, ALGORITHM
from app.core.config import get_session
from app.models.user import UserAccount, UserRole

# 1. 定义认证模式
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")

# 2. 核心依赖函数：从 Token 获取手机号
async def get_current_user_phone(token: str = Depends(oauth2_scheme)) -> str:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 解码 Token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        phone: str = payload.get("sub")
        if phone is None:
            raise credentials_exception
        return phone
    except JWTError:
        raise credentials_exception


async def get_current_user(
    phone: str = Depends(get_current_user_phone),
    session: AsyncSession = Depends(get_session)
) -> UserAccount:
    stmt = select(UserAccount).where(UserAccount.phone == phone)
    user = (await session.execute(stmt)).scalars().first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户不存在或已失效")
    return user


async def get_current_admin_user(current_user: UserAccount = Depends(get_current_user)) -> UserAccount:
    if current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要管理员权限")
    return current_user