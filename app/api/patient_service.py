from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List

from app.core.config import get_session
from app.core.security import verify_password  # 这里的引用其实用不到 verify，主要是为了鉴权
from fastapi.security import OAuth2PasswordBearer
from jose import jwt, JWTError
from app.core.security import SECRET_KEY, ALGORITHM
from app.models.user import UserAccount
from app.models.hospital import Patient, Department, Doctor, Registration, RegStatus
from app.schemas.hospital import PatientCreate, RegistrationCreate

router = APIRouter()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# --- 辅助函数：从 Token 获取当前登录用户的手机号 ---
async def get_current_user_phone(token: str = Depends(oauth2_scheme)) -> str:
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        phone: str = payload.get("sub")
        if phone is None:
            raise HTTPException(status_code=401, detail="无效的认证凭据")
        return phone
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的认证凭据")


# --- 1. 完善/创建患者档案 ---
@router.post("/profile", response_model=Patient)
async def create_patient_profile(
        profile: PatientCreate,
        phone: str = Depends(get_current_user_phone),
        session: AsyncSession = Depends(get_session)
):
    # 检查是否已经存在档案
    stmt = select(Patient).where(Patient.phone == phone)
    existing = (await session.execute(stmt)).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="档案已存在，请使用更新接口")

    # 创建新档案
    patient = Patient(phone=phone, **profile.dict())
    session.add(patient)
    await session.commit()
    await session.refresh(patient)
    return patient


# --- 2. 获取所有科室（用于挂号选择） ---
@router.get("/departments", response_model=List[Department])
async def get_departments(session: AsyncSession = Depends(get_session)):
    stmt = select(Department)
    result = await session.execute(stmt)
    return result.scalars().all()


# --- 3. 获取某科室下的医生 ---
@router.get("/doctors/{dept_id}", response_model=List[Doctor])
async def get_doctors_by_dept(dept_id: int, session: AsyncSession = Depends(get_session)):
    stmt = select(Doctor).where(Doctor.dept_id == dept_id)
    result = await session.execute(stmt)
    return result.scalars().all()


# --- 4. 提交挂号 ---
@router.post("/registrations", response_model=Registration)
async def create_registration(
        reg_in: RegistrationCreate,
        phone: str = Depends(get_current_user_phone),
        session: AsyncSession = Depends(get_session)
):
    # A. 找到当前用户的 PatientID
    stmt = select(Patient).where(Patient.phone == phone)
    patient = (await session.execute(stmt)).scalars().first()
    if not patient:
        raise HTTPException(status_code=400, detail="请先完善个人信息档案")

    # B. 计算费用 (这里简单模拟：专家号50，普通号10)
    fee = 50.0 if reg_in.reg_type == "专家号" else 10.0

    # C. 创建挂号单
    new_reg = Registration(
        patient_id=patient.patient_id,
        doctor_id=reg_in.doctor_id,
        reg_type=reg_in.reg_type,
        fee=fee,
        status=RegStatus.WAITING
    )

    session.add(new_reg)
    await session.commit()
    await session.refresh(new_reg)
    return new_reg