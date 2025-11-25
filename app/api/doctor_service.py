from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List

from app.core.config import get_session
# --- 修改点：从 deps 导入，不再依赖 patient_service ---
from app.api.deps import get_current_user_phone
from app.models.user import UserAccount, UserRole
from app.models.hospital import Doctor, Registration, RegStatus, MedicalRecord
from app.schemas.hospital import MedicalRecordCreate

router = APIRouter()


# --- 辅助函数：获取当前登录的医生对象 ---
async def get_current_doctor(
        phone: str = Depends(get_current_user_phone),
        session: AsyncSession = Depends(get_session)
) -> Doctor:
    user_stmt = select(UserAccount).where(UserAccount.phone == phone)
    user = (await session.execute(user_stmt)).scalars().first()
    if not user or user.role != UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="无权访问：仅限医生操作")

    doc_stmt = select(Doctor).where(Doctor.phone == phone)
    doctor = (await session.execute(doc_stmt)).scalars().first()
    if not doctor:
        raise HTTPException(status_code=404, detail="未找到您的医生档案信息")

    return doctor


# --- 接口 1: 医生排班 ---
@router.get("/schedule", response_model=List[Registration])
async def get_my_schedule(
        doctor: Doctor = Depends(get_current_doctor),
        session: AsyncSession = Depends(get_session)
):
    stmt = select(Registration).where(
        Registration.doctor_id == doctor.doctor_id,
        Registration.status == RegStatus.WAITING
    )
    result = await session.execute(stmt)
    return result.scalars().all()


# --- 接口 2: 接诊 ---
@router.post("/consultations/{reg_id}", response_model=MedicalRecord)
async def create_medical_record(
        reg_id: int,
        record_in: MedicalRecordCreate,
        doctor: Doctor = Depends(get_current_doctor),
        session: AsyncSession = Depends(get_session)
):
    stmt = select(Registration).where(Registration.reg_id == reg_id)
    registration = (await session.execute(stmt)).scalars().first()

    if not registration:
        raise HTTPException(status_code=404, detail="挂号单不存在")
    if registration.doctor_id != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="您只能处理自己的病人")
    if registration.status != RegStatus.WAITING:
        raise HTTPException(status_code=400, detail="该挂号单已处理或已取消")

    new_record = MedicalRecord(
        reg_id=reg_id,
        **record_in.dict()
    )
    session.add(new_record)

    registration.status = RegStatus.COMPLETED
    session.add(registration)

    await session.commit()
    await session.refresh(new_record)
    return new_record