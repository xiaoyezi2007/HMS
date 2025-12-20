from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import select, SQLModel
from typing import List, Optional
import io

from app.core.config import get_session
# --- 修改点：从 deps 导入，不再依赖 patient_service ---
from app.api.deps import get_current_user_phone
from app.models.user import UserAccount, UserRole
from app.models.hospital import (
    Doctor,
    Registration,
    RegStatus,
    MedicalRecord,
    Patient,
    Examination,
    Payment,
    PaymentType,
    Prescription,
    PrescriptionDetail,
    Ward,
    Hospitalization,
    ExamResult,
    Medicine,
    Nurse,
    NurseSchedule,
    NurseTask,
)
from app.schemas.hospital import MedicalRecordCreate
from app.schemas.hospital import ExaminationCreate, NurseTaskCreate
import random

router = APIRouter()


class HospitalizePayload(SQLModel):
    ward_id: int


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


def format_datetime(dt):
    if not dt:
        return ""
    return dt.strftime("%Y-%m-%d %H:%M")


async def pick_nurse_for_ward(session: AsyncSession, ward_id: int) -> Nurse:
    now = datetime.now()
    scheduled_stmt = (
        select(Nurse)
        .join(NurseSchedule, NurseSchedule.nurse_id == Nurse.nurse_id)
        .where(NurseSchedule.ward_id == ward_id)
        .where(NurseSchedule.start_time <= now, NurseSchedule.end_time >= now)
        .order_by(Nurse.is_head_nurse.desc(), NurseSchedule.start_time.desc())
    )
    scheduled_nurse = (await session.execute(scheduled_stmt)).scalars().first()
    if scheduled_nurse:
        return scheduled_nurse

    recent_stmt = (
        select(Nurse)
        .join(NurseSchedule, NurseSchedule.nurse_id == Nurse.nurse_id)
        .where(NurseSchedule.ward_id == ward_id)
        .order_by(NurseSchedule.end_time.desc())
    )
    recent_nurse = (await session.execute(recent_stmt)).scalars().first()
    if recent_nurse:
        return recent_nurse

    head_nurse = (await session.execute(select(Nurse).where(Nurse.is_head_nurse == True).order_by(Nurse.nurse_id))).scalars().first()
    if head_nurse:
        return head_nurse

    any_nurse = (await session.execute(select(Nurse).order_by(Nurse.nurse_id))).scalars().first()
    if not any_nurse:
        raise HTTPException(status_code=400, detail="暂无可分配的护士")
    return any_nurse


# --- 接口 1: 医生排班 ---
@router.get("/schedule", response_model=List[Registration])
async def get_my_schedule(
        doctor: Doctor = Depends(get_current_doctor),
        session: AsyncSession = Depends(get_session)
):
    # Auto-expire overdue registrations (WAITING and visit_date has passed)
    try:
        today = date.today()
        overdue_stmt = select(Registration).where(
            Registration.doctor_id == doctor.doctor_id,
            Registration.status == RegStatus.WAITING,
            Registration.visit_date < today,
        )
        overdue_regs = (await session.execute(overdue_stmt)).scalars().all()
        for reg in overdue_regs:
            reg.status = RegStatus.EXPIRED
            session.add(reg)

            pay_stmt = (
                select(Payment)
                .where(Payment.patient_id == reg.patient_id)
                .where(
                    or_(
                        Payment.type == PaymentType.REGISTRATION,
                        Payment.type == "挂号费",
                        Payment.type == "REGISTRATION",
                    )
                )
                .where(Payment.reg_id == reg.reg_id)
                .order_by(Payment.time.desc(), Payment.payment_id.desc())
            )
            pay = (await session.execute(pay_stmt)).scalars().first()
            if pay and getattr(pay, "status", "未缴费") != "已缴费":
                pay.status = "已取消"
                session.add(pay)

        if overdue_regs:
            await session.commit()
    except Exception:
        # best-effort; schedule should still load
        pass

    # 返回排队中和办理中的挂号，医生在完成办理后挂号会被标记为已结束并从列表中消失
    stmt = select(Registration).where(
        Registration.doctor_id == doctor.doctor_id,
        Registration.status.in_([RegStatus.WAITING, RegStatus.IN_PROGRESS])
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
    # 必须先开始办理（状态为办理中），才能书写病历
    if registration.status != RegStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="请先开始办理，再书写病历")

    # 如果已经存在病历，则将其视为更新（修改病历），保持 1:1 关系
    existing = (await session.execute(select(MedicalRecord).where(MedicalRecord.reg_id == reg_id))).scalars().first()
    if existing:
        existing.complaint = record_in.complaint
        existing.diagnosis = record_in.diagnosis
        existing.suggestion = record_in.suggestion
        session.add(existing)
        await session.commit()
        await session.refresh(existing)
        return existing

    new_record = MedicalRecord(
        reg_id=reg_id,
        **record_in.dict()
    )
    session.add(new_record)

    # 不在此处修改挂号状态，挂号的结束由医生在完成办理时统一设置为已完成
    await session.commit()
    await session.refresh(new_record)
    return new_record

# --- 新：为病历添加检查记录（医生操作，会随机生成结果） ---
@router.post("/consultations/{reg_id}/exams", response_model=Examination)
async def create_examination(
    reg_id: int,
    exam_in: ExaminationCreate,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_session)
):
    # 验证挂号与医生关联
    stmt = select(Registration).where(Registration.reg_id == reg_id)
    registration = (await session.execute(stmt)).scalars().first()
    if not registration:
        raise HTTPException(status_code=404, detail="挂号单不存在")
    if registration.doctor_id != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="您只能为自己的病人添加检查")

    # 必须存在病历才能添加检查
    rec_stmt = select(MedicalRecord).where(MedicalRecord.reg_id == reg_id)
    record = (await session.execute(rec_stmt)).scalars().first()
    if not record:
        raise HTTPException(status_code=404, detail="请先为该挂号建立病历，再添加检查")

    # 随机生成检查结果
    choices = [r.value for r in ExamResult]
    result = random.choice(choices)

    new_exam = Examination(
        type=exam_in.type,
        result=result,
        record_id=record.record_id
    )
    session.add(new_exam)
    await session.commit()
    await session.refresh(new_exam)
    # 创建对应的缴费（检查费），金额随机 50-200
    amt = random.randint(50, 200)
    # 避免重复创建：若已存在关联 exam_id 的 payment 则跳过
    try:
        pay_stmt = select(Payment).where(Payment.exam_id == new_exam.exam_id)
        existing_pay = (await session.execute(pay_stmt)).scalars().first()
    except Exception:
        existing_pay = None

    if not existing_pay:
        pay = Payment(type=PaymentType.EXAM, amount=amt, patient_id=registration.patient_id, exam_id=new_exam.exam_id)
        session.add(pay)
        await session.commit()
        await session.refresh(pay)

    return new_exam


# --- 新：列出挂号对应的检查记录（医生操作） ---
@router.get("/consultations/{reg_id}/exams")
async def list_examinations(
    reg_id: int,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_session)
):
    # 验证挂号与医生关联
    stmt = select(Registration).where(Registration.reg_id == reg_id)
    registration = (await session.execute(stmt)).scalars().first()
    if not registration:
        raise HTTPException(status_code=404, detail="挂号单不存在")
    if registration.doctor_id != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="您只能查看自己的病人的检查记录")

    rec_stmt = select(MedicalRecord).where(MedicalRecord.reg_id == reg_id)
    record = (await session.execute(rec_stmt)).scalars().first()
    if not record:
        return []

    exam_stmt = select(Examination).where(Examination.record_id == record.record_id)
    exams = (await session.execute(exam_stmt)).scalars().all()
    return exams


@router.get("/wards")
async def list_department_wards(
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Ward).where(Ward.dept_id == doctor.dept_id)
    wards = (await session.execute(stmt)).scalars().all()
    out = []
    for ward in wards:
        count_stmt = select(func.count()).where(
            Hospitalization.ward_id == ward.ward_id,
            Hospitalization.status == "在院"
        )
        occupied = (await session.execute(count_stmt)).scalar_one() or 0
        available = max(ward.bed_count - occupied, 0)
        out.append({
            "ward_id": ward.ward_id,
            "type": ward.type,
            "bed_count": ward.bed_count,
            "occupied": occupied,
            "available": available,
            "is_full": occupied >= ward.bed_count
        })
    return out


@router.get("/inpatients")
async def list_my_inpatients(
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_session)
):
    stmt = (
        select(Hospitalization, Ward, MedicalRecord, Registration, Patient)
        .join(Ward, Hospitalization.ward_id == Ward.ward_id)
        .join(MedicalRecord, Hospitalization.record_id == MedicalRecord.record_id)
        .join(Registration, MedicalRecord.reg_id == Registration.reg_id)
        .join(Patient, Registration.patient_id == Patient.patient_id)
        .where(Hospitalization.status == "在院")
        .where(Hospitalization.hosp_doctor_id == doctor.doctor_id)
    )

    rows = await session.execute(stmt)
    now = datetime.now()
    payload = []
    for hosp, ward, _, reg, patient in rows.all():
        stay_hours = max((now - hosp.in_date).total_seconds() / 3600, 0.0)
        payload.append({
            "hosp_id": hosp.hosp_id,
            "patient_id": patient.patient_id,
            "patient_name": patient.name,
            "ward_id": ward.ward_id,
            "ward_type": ward.type,
            "in_date": hosp.in_date,
            "stay_hours": stay_hours,
            "reg_id": reg.reg_id,
        })
    return payload


@router.get("/patients/{patient_id}/registrations/history")
async def get_patient_registration_history(
    patient_id: int,
    range: str = "current",
    current_reg_id: Optional[int] = None,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_session)
):
    patient = await session.get(Patient, patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在")

    allowed_ranges = {"current", "7d", "30d"}
    if range not in allowed_ranges:
        raise HTTPException(status_code=400, detail="range 仅支持 current、7d、30d")

    stmt = (
        select(Registration, MedicalRecord)
        .outerjoin(MedicalRecord, MedicalRecord.reg_id == Registration.reg_id)
        .where(Registration.patient_id == patient_id)
        .where(Registration.doctor_id == doctor.doctor_id)
    )

    if range == "current":
        if not current_reg_id:
            raise HTTPException(status_code=400, detail="current 范围需要提供 current_reg_id")
        stmt = stmt.where(Registration.reg_id == current_reg_id)
    else:
        days = 7 if range == "7d" else 30
        since = datetime.now() - timedelta(days=days)
        stmt = stmt.where(Registration.status == RegStatus.FINISHED)
        stmt = stmt.where(Registration.reg_date >= since)

    stmt = stmt.order_by(Registration.reg_date.desc())
    rows = await session.execute(stmt)
    entries = []
    raw_rows = rows.all()
    for reg, record in raw_rows:
        status_value = reg.status.value if hasattr(reg.status, "value") else reg.status
        entries.append({
            "reg_id": reg.reg_id,
            "reg_date": reg.reg_date,
            "visit_date": reg.visit_date,
            "status": status_value,
            "reg_type": reg.reg_type,
            "fee": float(reg.fee or 0),
            "patient_id": reg.patient_id,
            "doctor_id": reg.doctor_id,
            "is_current": bool(current_reg_id and reg.reg_id == current_reg_id),
            "record": (
                {
                    "record_id": record.record_id,
                    "complaint": record.complaint,
                    "diagnosis": record.diagnosis,
                    "suggestion": record.suggestion
                }
                if record else None
            )
        })

    if range == "current" and not entries:
        raise HTTPException(status_code=404, detail="未找到当前挂号记录")

    return entries


@router.get("/registrations/{reg_id}/detail")
async def get_registration_detail_for_doctor(
    reg_id: int,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_session)
):
    registration = await session.get(Registration, reg_id)
    if not registration:
        raise HTTPException(status_code=404, detail="挂号单不存在")
    if registration.doctor_id != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="您只能查看自己的挂号记录")

    record = (
        await session.execute(select(MedicalRecord).where(MedicalRecord.reg_id == reg_id))
    ).scalars().first()

    prescriptions_payload = []
    if record:
        pres_stmt = select(Prescription).where(Prescription.record_id == record.record_id)
        prescriptions = (await session.execute(pres_stmt)).scalars().all()
        for pres in prescriptions:
            details_stmt = select(PrescriptionDetail).where(PrescriptionDetail.pres_id == pres.pres_id)
            details = (await session.execute(details_stmt)).scalars().all()
            enriched = []
            for detail in details:
                medicine = await session.get(Medicine, detail.medicine_id)
                enriched.append({
                    "detail_id": detail.detail_id,
                    "medicine_id": detail.medicine_id,
                    "medicine_name": medicine.name if medicine else None,
                    "quantity": detail.quantity,
                    "usage": detail.usage,
                })
            prescriptions_payload.append({
                "pres_id": pres.pres_id,
                "create_time": pres.create_time,
                "total_amount": pres.total_amount,
                "status": pres.status,
                "details": enriched,
            })

    exams_payload = []
    if record:
        exam_stmt = select(Examination).where(Examination.record_id == record.record_id)
        exams = (await session.execute(exam_stmt)).scalars().all()
        for exam in exams:
            exams_payload.append({
                "exam_id": exam.exam_id,
                "type": exam.type,
                "result": exam.result,
                "date": exam.date,
                "record_id": exam.record_id,
                "reg_id": record.reg_id,
            })

    return {
        "registration": registration,
        "record": record,
        "prescriptions": prescriptions_payload,
        "exams": exams_payload,
        "admissions": []
    }


@router.post("/hospitalizations/{hosp_id}/tasks")
async def create_nurse_task(
    hosp_id: int,
    payload: NurseTaskCreate,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_session)
):
    hospitalization = await session.get(Hospitalization, hosp_id)
    if not hospitalization:
        raise HTTPException(status_code=404, detail="住院记录不存在")
    if hospitalization.hosp_doctor_id != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="您只能为自己负责的住院患者添加护理任务")
    if hospitalization.status != "在院":
        raise HTTPException(status_code=400, detail="仅能为在院患者添加护理任务")
    if not hospitalization.ward_id:
        raise HTTPException(status_code=400, detail="该住院记录缺少病房信息")

    nurse = await pick_nurse_for_ward(session, hospitalization.ward_id)
    task = NurseTask(
        type=payload.type,
        time=payload.time,
        nurse_id=nurse.nurse_id,
        hosp_id=hosp_id
    )
    session.add(task)
    await session.commit()
    await session.refresh(task)
    return task

# --- 新：根据挂号ID查询对应病历（仅限接诊该挂号的医生） ---
@router.get("/consultations/{reg_id}/record", response_model=MedicalRecord)
async def get_record_by_reg(
    reg_id: int,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Registration).where(Registration.reg_id == reg_id)
    registration = (await session.execute(stmt)).scalars().first()
    if not registration:
        raise HTTPException(status_code=404, detail="挂号单不存在")
    if registration.doctor_id != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="您只能查看自己的病人")

    rec_stmt = select(MedicalRecord).where(MedicalRecord.reg_id == reg_id)
    record = (await session.execute(rec_stmt)).scalars().first()
    if not record:
        raise HTTPException(status_code=404, detail="病历不存在")
    return record


# 新：根据挂号ID查询挂号信息与患者信息（仅限接诊该挂号的医生）
@router.get("/consultations/{reg_id}/info")
async def get_consultation_info(
    reg_id: int,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Registration).where(Registration.reg_id == reg_id)
    registration = (await session.execute(stmt)).scalars().first()
    if not registration:
        raise HTTPException(status_code=404, detail="挂号单不存在")
    if registration.doctor_id != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="您只能查看自己的挂号信息")

    patient = await session.get(Patient, registration.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="关联的患者不存在")

    return {"registration": registration, "patient": patient}


@router.post("/consultations/{reg_id}/hospitalize")
async def hospitalize_patient(
    reg_id: int,
    payload: HospitalizePayload,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Registration).where(Registration.reg_id == reg_id)
    registration = (await session.execute(stmt)).scalars().first()
    if not registration:
        raise HTTPException(status_code=404, detail="挂号单不存在")
    if registration.doctor_id != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="您只能为自己的病人办理住院")

    rec_stmt = select(MedicalRecord).where(MedicalRecord.reg_id == reg_id)
    record = (await session.execute(rec_stmt)).scalars().first()
    if not record:
        raise HTTPException(status_code=404, detail="请先建立病历再办理住院")

    ward = await session.get(Ward, payload.ward_id)
    if not ward or ward.dept_id != doctor.dept_id:
        raise HTTPException(status_code=400, detail="请选择当前科室的有效病房")

    count_stmt = select(func.count()).where(
        Hospitalization.ward_id == ward.ward_id,
        Hospitalization.status == "在院"
    )
    occupied = (await session.execute(count_stmt)).scalar_one() or 0
    if occupied >= ward.bed_count:
        raise HTTPException(status_code=400, detail="该病房已满，请选择其他病房")

    hosp = Hospitalization(
        ward_id=ward.ward_id,
        status="在院",
        hosp_doctor_id=doctor.doctor_id,
        record_id=record.record_id
    )
    session.add(hosp)
    try:
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        msg = str(getattr(exc, "orig", exc)).lower()
        if "uq_hosp_active_record_id" in msg or "duplicate entry" in msg:
            raise HTTPException(status_code=400, detail="该患者已在院，无法重复办理")
        raise HTTPException(status_code=400, detail="住院办理失败，请稍后再试")
    await session.refresh(hosp)
    return {"message": "住院办理完成", "hospitalization": hosp}


@router.get("/consultations/{reg_id}/transfer")
async def generate_transfer_form(
    reg_id: int,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Registration).where(Registration.reg_id == reg_id)
    registration = (await session.execute(stmt)).scalars().first()
    if not registration:
        raise HTTPException(status_code=404, detail="挂号单不存在")
    if registration.doctor_id != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="您只能为自己的病人申请转院")

    patient = await session.get(Patient, registration.patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail="关联患者不存在")

    rec_stmt = select(MedicalRecord).where(MedicalRecord.reg_id == reg_id)
    record = (await session.execute(rec_stmt)).scalars().first()

    exams = []
    if record:
        exam_stmt = select(Examination).where(Examination.record_id == record.record_id)
        exams = (await session.execute(exam_stmt)).scalars().all()

    lines = [
        "转院申请单",
        f"挂号ID：{registration.reg_id}",
        f"患者：{patient.name}（ID: {patient.patient_id}）", 
        f"联系方式：{patient.phone}",
        "",
        "【挂号信息】",
        f"挂号时间：{format_datetime(registration.reg_date)}",
        f"挂号类型：{registration.reg_type}",
        f"挂号状态：{registration.status}",
        "",
        "【病历摘要】"
    ]
    if record:
        lines.extend([
            f"主诉：{record.complaint}",
            f"诊断：{record.diagnosis}",
            f"建议：{record.suggestion}",
        ])
    else:
        lines.append("尚未填写病历")

    lines.append("")
    lines.append("【检查记录】")
    if exams:
        for exam in exams:
            lines.append(f"{exam.type} · 结果：{exam.result} · {format_datetime(exam.date)}")
    else:
        lines.append("暂未开具检查")

    content = "\n".join(lines)
    payload = io.BytesIO(content.encode("utf-8"))
    response = StreamingResponse(payload, media_type="text/plain")
    response.headers["content-disposition"] = f"attachment; filename=transfer_{reg_id}.txt"
    return response
# --- 新：开始办理（将 status 从 WAITING 改为 IN_PROGRESS） ---
@router.post("/consultations/{reg_id}/start")
async def start_handling(
    reg_id: int,
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
        raise HTTPException(status_code=400, detail="只有排队中的挂号可以开始办理")

    registration.status = RegStatus.IN_PROGRESS
    session.add(registration)
    await session.commit()
    await session.refresh(registration)
    return registration


# --- 新：完成办理（将 status 从 IN_PROGRESS 改为 FINISHED） ---
@router.post("/consultations/{reg_id}/finish")
async def finish_handling(
    reg_id: int,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Registration).where(Registration.reg_id == reg_id)
    registration = (await session.execute(stmt)).scalars().first()
    if not registration:
        raise HTTPException(status_code=404, detail="挂号单不存在")
    if registration.doctor_id != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="您只能处理自己的病人")
    if registration.status != RegStatus.IN_PROGRESS:
        raise HTTPException(status_code=400, detail="只有办理中的挂号可以完成办理")

    registration.status = RegStatus.FINISHED
    session.add(registration)
    await session.commit()
    await session.refresh(registration)
    # 挂号完成时，如果存在处方，则为处方生成缴费记录（处方费）
    try:
        rec = (await session.execute(select(MedicalRecord).where(MedicalRecord.reg_id == reg_id))).scalars().first()
        if rec:
            pres = (await session.execute(select(Prescription).where(Prescription.record_id == rec.record_id))).scalars().first()
        else:
            pres = None
    except Exception:
        pres = None

    if pres and pres.total_amount and pres.total_amount > 0:
        # 若已有与该处方关联的 payment 则跳过创建
        pay_stmt = select(Payment).where(Payment.pres_id == pres.pres_id)
        existing_pay = (await session.execute(pay_stmt)).scalars().first()
        if not existing_pay:
            pay = Payment(type=PaymentType.PRESCRIPTION, amount=pres.total_amount, patient_id=registration.patient_id, pres_id=pres.pres_id)
            session.add(pay)
            await session.commit()

    return registration