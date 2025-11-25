from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List

from app.core.config import get_session
from app.api.patient_service import get_current_user_phone
from app.models.user import UserAccount, UserRole
from app.models.hospital import Doctor, Registration, RegStatus, MedicalRecord
from app.schemas.hospital import MedicalRecordCreate

router = APIRouter()


# --- 辅助函数：获取当前登录的医生对象 ---
async def get_current_doctor(
        phone: str = Depends(get_current_user_phone),
        session: AsyncSession = Depends(get_session)
) -> Doctor:
    # 1. 确认账号角色是医生
    user_stmt = select(UserAccount).where(UserAccount.phone == phone)
    user = (await session.execute(user_stmt)).scalars().first()
    if not user or user.role != UserRole.DOCTOR:
        raise HTTPException(status_code=403, detail="无权访问：仅限医生操作")

    # 2. 通过手机号找到 Doctor 表里的记录
    doc_stmt = select(Doctor).where(Doctor.phone == phone)
    doctor = (await session.execute(doc_stmt)).scalars().first()
    if not doctor:
        raise HTTPException(status_code=404, detail="未找到您的医生档案信息")

    return doctor


# --- 1. 医生查看待诊列表 ---
@router.get("/schedule", response_model=List[Registration])
async def get_my_schedule(
        doctor: Doctor = Depends(get_current_doctor),
        session: AsyncSession = Depends(get_session)
):
    # 查询：该医生的、状态为“待就诊”的挂号单
    stmt = select(Registration).where(
        Registration.doctor_id == doctor.doctor_id,
        Registration.status == RegStatus.WAITING
    )
    result = await session.execute(stmt)
    return result.scalars().all()


# --- 2. 医生接诊（写病历） ---
@router.post("/consultations/{reg_id}", response_model=MedicalRecord)
async def create_medical_record(
        reg_id: int,
        record_in: MedicalRecordCreate,
        doctor: Doctor = Depends(get_current_doctor),
        session: AsyncSession = Depends(get_session)
):
    # A. 检查挂号单是否存在且属于该医生
    stmt = select(Registration).where(Registration.reg_id == reg_id)
    registration = (await session.execute(stmt)).scalars().first()

    if not registration:
        raise HTTPException(status_code=404, detail="挂号单不存在")
    if registration.doctor_id != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="您只能处理自己的病人")
    if registration.status != RegStatus.WAITING:
        raise HTTPException(status_code=400, detail="该挂号单已处理或已取消")

    # B. 创建病历
    new_record = MedicalRecord(
        reg_id=reg_id,
        **record_in.dict()
    )
    session.add(new_record)

    # C. 更新挂号单状态为“已就诊”
    registration.status = RegStatus.COMPLETED
    session.add(registration)

    await session.commit()
    await session.refresh(new_record)
    return new_record