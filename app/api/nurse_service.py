from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, func
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
    TodayTaskItem,
    WardTaskItem,
)

from app.services.billing import (
    DEFAULT_HOSPITAL_HOURLY_RATE,
    compute_hospitalization_bill,
)

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


ScheduleEntry = Tuple[NurseSchedule, Nurse]
ScheduleMap = Dict[int, List[ScheduleEntry]]


async def load_schedule_map(session: AsyncSession, ward_ids: List[int]) -> ScheduleMap:
    if not ward_ids:
        return {}
    stmt = (
        select(NurseSchedule, Nurse)
        .join(Nurse, NurseSchedule.nurse_id == Nurse.nurse_id)
        .where(NurseSchedule.ward_id.in_(ward_ids))
    )
    rows = await session.execute(stmt)
    schedule_map: ScheduleMap = {}
    for schedule, nurse in rows.all():
        bucket = schedule_map.setdefault(schedule.ward_id, [])
        bucket.append((schedule, nurse))
    for bucket in schedule_map.values():
        bucket.sort(key=lambda entry: (entry[0].start_time, entry[0].end_time, entry[0].nurse_id))
    return schedule_map


def resolve_on_duty_nurse(schedule_map: ScheduleMap, ward_id: Optional[int], target_time: datetime) -> Optional[Nurse]:
    if ward_id is None:
        return None
    for schedule, nurse in schedule_map.get(ward_id, []):
        if schedule.start_time <= target_time <= schedule.end_time:
            return nurse
    return None


async def nurse_has_assignment(
        session: AsyncSession,
        nurse: Nurse,
        ward_id: Optional[int],
        target_time: datetime
) -> bool:
    if ward_id is None:
        return False
    stmt = select(NurseSchedule).where(
        NurseSchedule.nurse_id == nurse.nurse_id,
        NurseSchedule.ward_id == ward_id,
        NurseSchedule.start_time <= target_time,
        NurseSchedule.end_time >= target_time,
    )
    assigned = (await session.execute(stmt)).scalars().first()
    return assigned is not None


async def _expire_overdue_tasks(session: AsyncSession, task_ids: list[int]) -> None:
    if not task_ids:
        return
    now = datetime.now()
    stmt = select(NurseTask).where(NurseTask.task_id.in_(task_ids))
    tasks = (await session.execute(stmt)).scalars().all()
    dirty = False
    for task in tasks:
        if task.status == "未完成" and task.time < now:
            task.status = "已过期"
            session.add(task)
            dirty = True
    if dirty:
        await session.commit()


@router.get("/profile", response_model=NurseProfile)
async def get_nurse_profile(
    nurse: Nurse = Depends(get_current_nurse)
):
    return NurseProfile(nurse_id=nurse.nurse_id, name=nurse.name, is_head_nurse=nurse.is_head_nurse)


@router.get("/today_tasks", response_model=List[TodayTaskItem])
async def list_today_tasks(
    nurse: Nurse = Depends(get_current_nurse),
    session: AsyncSession = Depends(get_session)
):
    today = datetime.now().date()
    start = datetime.combine(today, datetime.min.time())
    end = start + timedelta(days=1)

    stmt = (
        select(NurseTask, Patient, Hospitalization.ward_id)
        .join(Hospitalization, NurseTask.hosp_id == Hospitalization.hosp_id)
        .join(MedicalRecord, Hospitalization.record_id == MedicalRecord.record_id)
        .join(Registration, MedicalRecord.reg_id == Registration.reg_id)
        .join(Patient, Registration.patient_id == Patient.patient_id)
        .where(NurseTask.time >= start, NurseTask.time < end)
    )

    rows = (await session.execute(stmt)).all()
    task_ids = [t.task_id for t, _, _ in rows]
    await _expire_overdue_tasks(session, task_ids)

    ward_ids = [ward_id for _, _, ward_id in rows if ward_id is not None]
    schedule_map = await load_schedule_map(session, list(set(ward_ids)))

    payload: List[TodayTaskItem] = []
    now = datetime.now()
    for task, patient, ward_id in rows:
        assigned_nurse = resolve_on_duty_nurse(schedule_map, ward_id, task.time)
        if not nurse.is_head_nurse:
            if not assigned_nurse or assigned_nurse.nurse_id != nurse.nurse_id:
                continue

        status = task.status
        if status == "未完成" and task.time < now:
            status = "已过期"
        nurse_name = assigned_nurse.name if assigned_nurse else "未排班"
        payload.append(TodayTaskItem(
            task_id=task.task_id,
            patient_name=patient.name,
            type=task.type,
            time=task.time,
            status=status,
            nurse_name=nurse_name,
        ))

    payload.sort(key=lambda item: item.time)
    return payload


@router.get("/my_schedules", response_model=List[ScheduleRead])
async def get_my_schedules(
    include_history: bool = Query(False, description="是否包含历史排班"),
    nurse: Nurse = Depends(get_current_nurse),
    session: AsyncSession = Depends(get_session)
):
    now = datetime.now()
    stmt = select(NurseSchedule, Ward).join(Ward).where(
        NurseSchedule.nurse_id == nurse.nurse_id,
    )
    if not include_history:
        stmt = stmt.where(NurseSchedule.end_time >= now)
    stmt = stmt.order_by(NurseSchedule.start_time.desc())

    results = await session.execute(stmt)

    schedule_list = []
    for schedule, ward in results:
        schedule_list.append(ScheduleRead(
            schedule_id=schedule.schedule_id,
            ward_id=ward.ward_id,
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

    now = datetime.now()
    schedule_stmt = select(NurseSchedule, Nurse).join(Nurse, NurseSchedule.nurse_id == Nurse.nurse_id).where(
        NurseSchedule.end_time >= now
    )
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

    occupancy_stmt = (
        select(Hospitalization.ward_id, func.count().label("occupied"))
        .where(Hospitalization.status == "在院")
        .group_by(Hospitalization.ward_id)
    )
    occupancy_rows = await session.execute(occupancy_stmt)
    occupancy_map = {row.ward_id: row.occupied for row in occupancy_rows}

    return [
        WardOverviewItem(
            ward_id=w.ward_id,
            ward_type=w.type,
            bed_count=w.bed_count,
            occupied_count=int(occupancy_map.get(w.ward_id, 0)),
        )
        for w in wards
    ]


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


@router.get("/ward/{ward_id}/tasks", response_model=List[WardTaskItem])
async def list_ward_tasks(
        ward_id: int,
        nurse: Nurse = Depends(get_current_nurse),
        session: AsyncSession = Depends(get_session)
):
    ward = await session.get(Ward, ward_id)
    if not ward:
        raise HTTPException(status_code=404, detail="病房不存在")

    if not nurse.is_head_nurse:
        assigned_stmt = select(NurseSchedule).where(
            NurseSchedule.nurse_id == nurse.nurse_id,
            NurseSchedule.ward_id == ward_id
        )
        assigned = (await session.execute(assigned_stmt)).scalars().first()
        if not assigned:
            raise HTTPException(status_code=403, detail="无权查看该病房")

    hosp_stmt = select(Hospitalization.hosp_id).where(
        Hospitalization.ward_id == ward_id,
        Hospitalization.status == "在院",
    )
    hosp_ids = (await session.execute(hosp_stmt)).scalars().all()
    if not hosp_ids:
        return []

    stmt = (
        select(NurseTask, Patient, Hospitalization.ward_id)
        .join(Hospitalization, NurseTask.hosp_id == Hospitalization.hosp_id)
        .join(MedicalRecord, Hospitalization.record_id == MedicalRecord.record_id)
        .join(Registration, MedicalRecord.reg_id == Registration.reg_id)
        .join(Patient, Registration.patient_id == Patient.patient_id)
        .where(NurseTask.hosp_id.in_(hosp_ids))
        .order_by(NurseTask.time.asc(), NurseTask.task_id.asc())
    )

    rows = (await session.execute(stmt)).all()
    task_ids = [t.task_id for t, _, _ in rows]
    await _expire_overdue_tasks(session, task_ids)

    schedule_map = await load_schedule_map(session, [ward_id])
    now = datetime.now()
    payload: List[WardTaskItem] = []
    for task, patient, ward_ref in rows:
        status = task.status
        if status == "未完成" and task.time < now:
            status = "已过期"
        assigned_nurse = resolve_on_duty_nurse(schedule_map, ward_ref, task.time)
        payload.append(WardTaskItem(
            task_id=task.task_id,
            hosp_id=task.hosp_id,
            patient_name=patient.name,
            type=task.type,
            time=task.time,
            status=status,
            nurse_name=assigned_nurse.name if assigned_nurse else "未排班",
        ))
    return payload


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

    for nurse_id in payload.nurse_ids:
        session.add(NurseSchedule(
            nurse_id=nurse_id,
            ward_id=payload.ward_id,
            start_time=payload.start_time,
            end_time=payload.end_time
        ))

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

    await session.commit()
    total_records = len(wards) * shift_count
    return {"detail": f"已自动生成 {total_records} 条排班记录"}


@router.post("/tasks/{task_id}/complete")
async def complete_task(
        task_id: int,
        nurse: Nurse = Depends(get_current_nurse),
        session: AsyncSession = Depends(get_session)
):
    task = await session.get(NurseTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    hospitalization = await session.get(Hospitalization, task.hosp_id)
    ward_id = hospitalization.ward_id if hospitalization else None
    if not nurse.is_head_nurse:
        assigned = await nurse_has_assignment(session, nurse, ward_id, task.time)
        if not assigned:
            raise HTTPException(status_code=403, detail="仅当前排班护士可以完成该任务")

    if task.status == "已完成":
        return {"detail": "任务已完成"}

    # 若已过期，保持状态不变，仅提示；前端可自行隐藏
    if task.status == "已过期":
        return {"detail": "任务已过期", "status": task.status}

    now = datetime.now()
    if task.time < now and task.status == "未完成":
        task.status = "已过期"
    else:
        task.status = "已完成"

    session.add(task)
    await session.commit()
    return {"detail": "任务状态已更新", "status": task.status}


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
    bill = await compute_hospitalization_bill(
        session,
        hospitalization,
        DEFAULT_HOSPITAL_HOURLY_RATE,
        reference_end=out_date,
    )
    amount = bill["total_fee"]

    hospitalization.status = "已出院"
    hospitalization.out_date = out_date
    session.add(hospitalization)

    payment = Payment(
        type=PaymentType.HOSPITAL,
        amount=amount,
        status="未缴费",
        patient_id=patient.patient_id,
        reg_id=registration.reg_id,
        hosp_id=hospitalization.hosp_id
    )
    session.add(payment)

    await session.commit()
    await session.refresh(payment)

    return {
        "detail": "出院办理完成",
        "bill_amount": amount,
        "bill_breakdown": bill,
        "payment_id": payment.payment_id
    }