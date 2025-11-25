from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List

from app.core.config import get_session
# --- 修改点：从 deps 导入 ---
from app.api.deps import get_current_user_phone
from app.models.hospital import Patient, Department, Doctor, Registration, RegStatus
from app.schemas.hospital import PatientCreate, RegistrationCreate

router = APIRouter()


# --- 接口 1: 完善/创建患者档案 ---
@router.post("/profile", response_model=Patient)
async def create_patient_profile(
        profile: PatientCreate,
        phone: str = Depends(get_current_user_phone),  # 直接使用导入的函数
        session: AsyncSession = Depends(get_session)
):
    stmt = select(Patient).where(Patient.phone == phone)
    existing = (await session.execute(stmt)).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="档案已存在，请使用更新接口")

    patient = Patient(phone=phone, **profile.dict())
    session.add(patient)
    await session.commit()
    await session.refresh(patient)
    return patient


# --- 接口 2: 获取所有科室 ---
@router.get("/departments", response_model=List[Department])
async def get_departments(session: AsyncSession = Depends(get_session)):
    stmt = select(Department)
    result = await session.execute(stmt)
    return result.scalars().all()


# --- 接口 3: 获取医生 ---
@router.get("/doctors/{dept_id}", response_model=List[Doctor])
async def get_doctors_by_dept(dept_id: int, session: AsyncSession = Depends(get_session)):
    stmt = select(Doctor).where(Doctor.dept_id == dept_id)
    result = await session.execute(stmt)
    return result.scalars().all()


# --- 接口 4: 挂号 ---
@router.post("/registrations", response_model=Registration)
async def create_registration(
        reg_in: RegistrationCreate,
        phone: str = Depends(get_current_user_phone),  # 直接使用导入的函数
        session: AsyncSession = Depends(get_session)
):
    stmt = select(Patient).where(Patient.phone == phone)
    patient = (await session.execute(stmt)).scalars().first()
    if not patient:
        raise HTTPException(status_code=400, detail="请先完善个人信息档案")

    fee = 50.0 if reg_in.reg_type == "专家号" else 10.0

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