from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List

from app.core.config import get_session
from app.api.deps import get_current_user_phone
from app.models.hospital import Doctor, Medicine, Prescription, PrescriptionDetail, MedicalRecord
from app.schemas.pharmacy import PrescriptionCreate, PrescriptionRead

router = APIRouter()


# 简单的医生验证
async def get_current_doctor(
        phone: str = Depends(get_current_user_phone),
        session: AsyncSession = Depends(get_session)
) -> Doctor:
    doc = (await session.execute(select(Doctor).where(Doctor.phone == phone))).scalars().first()
    if not doc:
        raise HTTPException(status_code=403, detail="无权操作")
    return doc


@router.get("/medicines", response_model=List[Medicine])
async def get_medicines(session: AsyncSession = Depends(get_session)):
    return (await session.execute(select(Medicine).where(Medicine.stock > 0))).scalars().all()


@router.post("/prescriptions", response_model=PrescriptionRead)
async def create_prescription(
        pres_in: PrescriptionCreate,
        doctor: Doctor = Depends(get_current_doctor),
        session: AsyncSession = Depends(get_session)
):
    # 简化版逻辑，省略了部分校验以缩短篇幅，确保能跑通
    new_pres = Prescription(record_id=pres_in.record_id, total_amount=0.0)
    session.add(new_pres)
    await session.flush()

    total = 0.0
    for item in pres_in.items:
        med = await session.get(Medicine, item.medicine_id)
        if not med or med.stock < item.quantity:
            raise HTTPException(400, "库存不足")
        med.stock -= item.quantity
        session.add(med)
        total += med.price * item.quantity
        session.add(PrescriptionDetail(pres_id=new_pres.pres_id, medicine_id=item.medicine_id, quantity=item.quantity,
                                       usage=item.usage))

    new_pres.total_amount = total
    session.add(new_pres)
    await session.commit()
    await session.refresh(new_pres)
    return new_pres