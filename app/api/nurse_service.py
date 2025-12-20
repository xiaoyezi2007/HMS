from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.core.config import get_session
# 关键：从 deps 导入，防止循环引用
from app.api.deps import get_current_user_phone
from app.models.user import UserAccount, UserRole
from app.models.hospital import (
    Nurse,
    NurseSchedule,
    Ward,
    Hospitalization,
    MedicalRecord,
    Registration,
    Patient,
    Payment,
    PaymentType,
    NurseTask,
)
from app.schemas.nurse import (
    ScheduleRead,
    NurseProfile,
    HeadScheduleContext,
    NurseOption,
    WardScheduleEntry,
    WardScheduleGroup,
    WardOverviewItem,
    WardRecordItem,
    ScheduleUpsertPayload,
    AutoScheduleRequest,
)

HOSPITAL_HOURLY_RATE = 80.0

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


async def get_head_nurse(
        nurse: Nurse = Depends(get_current_nurse)
) -> Nurse:
    if not nurse.is_head_nurse:
        raise HTTPException(status_code=403, detail="仅护士长可以执行该操作")
    return nurse


async def assign_tasks_to_ward(session: AsyncSession, ward_id: int, nurse_id: int) -> None:
    hosp_stmt = select(Hospitalization.hosp_id).where(
        Hospitalization.ward_id == ward_id,
        Hospitalization.status == "在院",
    )
    hosp_ids = (await session.execute(hosp_stmt)).scalars().all()
    if not hosp_ids:
        return

    task_stmt = select(NurseTask).where(NurseTask.hosp_id.in_(hosp_ids))
    tasks = (await session.execute(task_stmt)).scalars().all()
    for task in tasks:
        task.nurse_id = nurse_id
        session.add(task)


@router.get("/profile", response_model=NurseProfile)
async def get_nurse_profile(
    nurse: Nurse = Depends(get_current_nurse)
):
    return NurseProfile(nurse_id=nurse.nurse_id, name=nurse.name, is_head_nurse=nurse.is_head_nurse)


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
            start_time=schedule.start_time,
            end_time=schedule.end_time
        ))
    return schedule_list


@router.get("/head/context", response_model=HeadScheduleContext)
async def get_head_schedule_context(
        _: Nurse = Depends(get_head_nurse),
        session: AsyncSession = Depends(get_session)
):
    ward_result = await session.execute(select(Ward))
    wards = ward_result.scalars().all()
    ward_map = {}
    ward_payload: List[WardScheduleGroup] = []
    for ward in wards:
        group = WardScheduleGroup(ward_id=ward.ward_id, ward_type=ward.type, schedules=[])
        ward_map[ward.ward_id] = group
        ward_payload.append(group)

    schedule_stmt = select(NurseSchedule, Nurse).join(Nurse, NurseSchedule.nurse_id == Nurse.nurse_id)
    schedule_rows = await session.execute(schedule_stmt)
    for schedule, nurse in schedule_rows.all():
        ward_entry = ward_map.get(schedule.ward_id)
        if not ward_entry:
            continue
        ward_entry.schedules.append(WardScheduleEntry(
            schedule_id=schedule.schedule_id,
            nurse_id=schedule.nurse_id,
            nurse_name=nurse.name,
            start_time=schedule.start_time,
            end_time=schedule.end_time
        ))

    for group in ward_payload:
        group.schedules.sort(key=lambda s: (s.start_time, s.end_time, s.nurse_id))

    nurse_rows = (await session.execute(select(Nurse))).scalars().all()
    nurse_options = [NurseOption(nurse_id=n.nurse_id, name=n.name, is_head_nurse=n.is_head_nurse) for n in nurse_rows]
    return HeadScheduleContext(wards=ward_payload, nurses=nurse_options)


@router.get("/ward_overview", response_model=List[WardOverviewItem])
async def get_ward_overview(
        nurse: Nurse = Depends(get_current_nurse),
        session: AsyncSession = Depends(get_session)
):
    if nurse.is_head_nurse:
        ward_stmt = select(Ward)
    else:
        ward_stmt = select(Ward).join(NurseSchedule, NurseSchedule.ward_id == Ward.ward_id).where(
            NurseSchedule.nurse_id == nurse.nurse_id
        )
    wards = (await session.execute(ward_stmt)).scalars().unique().all()
    return [WardOverviewItem(ward_id=w.ward_id, ward_type=w.type, bed_count=w.bed_count) for w in wards]


@router.get("/ward/{ward_id}/records", response_model=List[WardRecordItem])
async def list_ward_records(
        ward_id: int,
        nurse: Nurse = Depends(get_current_nurse),
        session: AsyncSession = Depends(get_session)
):
    ward = await session.get(Ward, ward_id)
    if not ward:
        raise HTTPException(status_code=404, detail="病房不存在")

    if not nurse.is_head_nurse:
        # 普通护士只能查看自己排班的病房
        assigned_stmt = select(NurseSchedule).where(
            NurseSchedule.nurse_id == nurse.nurse_id,
            NurseSchedule.ward_id == ward_id
        )
        assigned = (await session.execute(assigned_stmt)).scalars().first()
        if not assigned:
            raise HTTPException(status_code=403, detail="无权查看该病房")

    stmt = (
        select(Hospitalization, MedicalRecord, Registration, Patient)
        .join(MedicalRecord, Hospitalization.record_id == MedicalRecord.record_id)
        .join(Registration, MedicalRecord.reg_id == Registration.reg_id)
        .join(Patient, Registration.patient_id == Patient.patient_id)
        .where(Hospitalization.ward_id == ward_id, Hospitalization.status == "在院")
    )

    rows = (await session.execute(stmt)).all()
    records: List[WardRecordItem] = []
    for hosp, record, _, patient in rows:
        records.append(WardRecordItem(
            ward_id=ward.ward_id,
            ward_type=ward.type,
            hosp_id=hosp.hosp_id,
            record_id=record.record_id,
            patient_id=patient.patient_id,
            patient_name=patient.name,
            complaint=record.complaint,
            diagnosis=record.diagnosis,
            suggestion=record.suggestion,
            in_date=hosp.in_date,
        ))
    return records


@router.post("/head/schedules/upsert")
async def upsert_schedule_slot(
        payload: ScheduleUpsertPayload,
        _: Nurse = Depends(get_head_nurse),
        session: AsyncSession = Depends(get_session)
):
    if payload.end_time <= payload.start_time:
        raise HTTPException(status_code=400, detail="结束时间必须晚于开始时间")

    ward = await session.get(Ward, payload.ward_id)
    if not ward:
        raise HTTPException(status_code=404, detail="病房不存在")

    if payload.nurse_ids:
        nurse_stmt = select(Nurse.nurse_id).where(Nurse.nurse_id.in_(payload.nurse_ids))
        found_ids = set((await session.execute(nurse_stmt)).scalars().all())
        if len(found_ids) != len(set(payload.nurse_ids)):
            raise HTTPException(status_code=400, detail="存在无效的护士ID")

    target_ward_id = payload.source_ward_id or payload.ward_id
    target_start = payload.source_start_time or payload.start_time
    target_end = payload.source_end_time or payload.end_time

    del_stmt = delete(NurseSchedule).where(
        NurseSchedule.ward_id == target_ward_id,
        NurseSchedule.start_time == target_start,
        NurseSchedule.end_time == target_end
    )
    await session.execute(del_stmt)

    if not payload.nurse_ids:
        await session.commit()
        return {"detail": "排班已更新"}

    target_nurse_id = payload.nurse_ids[0]
    for nurse_id in payload.nurse_ids:
        session.add(NurseSchedule(
            nurse_id=nurse_id,
            ward_id=payload.ward_id,
            start_time=payload.start_time,
            end_time=payload.end_time
        ))

    await assign_tasks_to_ward(session, payload.ward_id, target_nurse_id)

    await session.commit()
    return {"detail": "排班已更新"}


@router.delete("/head/schedules/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule_entry(
        schedule_id: int,
        _: Nurse = Depends(get_head_nurse),
        session: AsyncSession = Depends(get_session)
):
    schedule = await session.get(NurseSchedule, schedule_id)
    if not schedule:
        raise HTTPException(status_code=404, detail="排班记录不存在")
    await session.delete(schedule)
    await session.commit()


@router.post("/head/schedules/auto")
async def auto_generate_schedules(
        payload: AutoScheduleRequest,
        _: Nurse = Depends(get_head_nurse),
        session: AsyncSession = Depends(get_session)
):
    start_time = payload.start_time or datetime.now()
    now = datetime.now()
    shift_hours = payload.shift_hours or 8
    shift_count = payload.shift_count or 3

    ward_stmt = (
        select(Ward)
        .join(Hospitalization, Hospitalization.ward_id == Ward.ward_id)
        .where(Hospitalization.status == "在院")
    )
    if payload.ward_ids:
        ward_stmt = ward_stmt.where(Ward.ward_id.in_(payload.ward_ids))
    wards = (await session.execute(ward_stmt)).scalars().unique().all()
    if not wards:
        raise HTTPException(status_code=400, detail="未找到可排班的病房")

    nurse_stmt = select(Nurse).where(Nurse.is_head_nurse == False)
    nurses = (await session.execute(nurse_stmt)).scalars().all()
    if not nurses:
        nurses = (await session.execute(select(Nurse))).scalars().all()
    if not nurses:
        raise HTTPException(status_code=400, detail="暂无可排班的护士")

    ward_ids = [w.ward_id for w in wards]
    window_end = start_time + timedelta(hours=shift_hours * shift_count)
    del_stmt = delete(NurseSchedule).where(
        NurseSchedule.ward_id.in_(ward_ids),
        NurseSchedule.start_time >= start_time,
        NurseSchedule.start_time < window_end
    )
    await session.execute(del_stmt)

    cursor = 0
    first_assignment = {}
    for shift_index in range(shift_count):
        slot_time = start_time + timedelta(hours=shift_hours * shift_index)
        slot_end = slot_time + timedelta(hours=shift_hours)
        for ward in wards:
            nurse = nurses[cursor % len(nurses)]
            session.add(NurseSchedule(
                nurse_id=nurse.nurse_id,
                ward_id=ward.ward_id,
                start_time=slot_time,
                end_time=slot_end
            ))
            cursor += 1

            if ward.ward_id not in first_assignment and (slot_time <= now < slot_end or slot_time >= now):
                first_assignment[ward.ward_id] = nurse.nurse_id

    for ward_id, nurse_id in first_assignment.items():
        await assign_tasks_to_ward(session, ward_id, nurse_id)

    await session.commit()
    total_records = len(wards) * shift_count
    return {"detail": f"已自动生成 {total_records} 条排班记录"}


@router.get("/head/inpatients")
async def list_active_inpatients(
        _: Nurse = Depends(get_head_nurse),
        session: AsyncSession = Depends(get_session)
):
    stmt = (
        select(Hospitalization, Ward, MedicalRecord, Registration, Patient)
        .join(Ward, Hospitalization.ward_id == Ward.ward_id)
        .join(MedicalRecord, Hospitalization.record_id == MedicalRecord.record_id)
        .join(Registration, MedicalRecord.reg_id == Registration.reg_id)
        .join(Patient, Registration.patient_id == Patient.patient_id)
        .where(Hospitalization.status == "在院")
    )

    rows = await session.execute(stmt)
    now = datetime.now()
    payload = []
    for hosp, ward, _, _, patient in rows.all():
        stay_hours = max((now - hosp.in_date).total_seconds() / 3600, 0.0)
        payload.append({
            "hosp_id": hosp.hosp_id,
            "patient_id": patient.patient_id,
            "patient_name": patient.name,
            "ward_type": ward.type,
            "in_date": hosp.in_date,
            "stay_hours": stay_hours,
        })
    return payload


@router.post("/head/hospitalizations/{hosp_id}/discharge")
async def discharge_inpatient(
        hosp_id: int,
        _: Nurse = Depends(get_head_nurse),
        session: AsyncSession = Depends(get_session)
):
    hospitalization = await session.get(Hospitalization, hosp_id)
    if not hospitalization:
        raise HTTPException(status_code=404, detail="住院记录不存在")
    if hospitalization.status != "在院":
        raise HTTPException(status_code=400, detail="该患者已办理出院")

    record = await session.get(MedicalRecord, hospitalization.record_id) if hospitalization.record_id else None
    if not record:
        raise HTTPException(status_code=400, detail="缺少关联病历，无法办理出院")

    registration = await session.get(Registration, record.reg_id)
    if not registration:
        raise HTTPException(status_code=400, detail="缺少关联挂号记录")

    patient = await session.get(Patient, registration.patient_id)
    if not patient:
        raise HTTPException(status_code=400, detail="缺少患者信息")

    out_date = datetime.now()
    stay_hours = max((out_date - hospitalization.in_date).total_seconds() / 3600, 0.5)
    amount = round(stay_hours * HOSPITAL_HOURLY_RATE, 2)

    hospitalization.status = "已出院"
    hospitalization.out_date = out_date
    session.add(hospitalization)

    payment = Payment(
        type=PaymentType.HOSPITAL,
        amount=amount,
        status="未缴费",
        patient_id=patient.patient_id,
        hosp_id=hospitalization.hosp_id
    )
    session.add(payment)

    await session.commit()
    await session.refresh(payment)

    return {
        "detail": "出院办理完成",
        "bill_amount": amount,
        "stay_hours": stay_hours,
        "payment_id": payment.payment_id
    }