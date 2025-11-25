from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List

from app.core.config import get_session
# 关键：从 deps 导入，防止循环引用
from app.api.deps import get_current_user_phone
from app.models.user import UserAccount, UserRole
from app.models.hospital import Nurse, NurseSchedule, Ward
from app.schemas.nurse import ScheduleRead

router = APIRouter()


async def get_current_nurse(
        phone: str = Depends(get_current_user_phone),
        session: AsyncSession = Depends(get_session)
) -> Nurse:
    user = (await session.execute(select(UserAccount).where(UserAccount.phone == phone))).scalars().first()
    if not user or user.role != UserRole.NURSE:
        raise HTTPException(status_code=403, detail="无权访问")

    nurse = (await session.execute(select(Nurse).where(Nurse.phone == phone))).scalars().first()
    if not nurse:
        raise HTTPException(status_code=404, detail="未找到档案")
    return nurse


@router.get("/my_schedules", response_model=List[ScheduleRead])
async def get_my_schedules(
        nurse: Nurse = Depends(get_current_nurse),
        session: AsyncSession = Depends(get_session)
):
    stmt = select(NurseSchedule, Ward).join(Ward).where(NurseSchedule.nurse_id == nurse.nurse_id)
    results = await session.execute(stmt)

    schedule_list = []
    for schedule, ward in results:
        schedule_list.append(ScheduleRead(
            schedule_id=schedule.schedule_id,
            nurse_name=nurse.name,
            ward_type=ward.type,
            time=schedule.time
        ))
    return schedule_list