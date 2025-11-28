from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List

from app.core.config import get_session
# --- 修改点：从 deps 导入，不再依赖 patient_service ---
from app.api.deps import get_current_user_phone
from app.models.user import UserAccount, UserRole
from app.models.hospital import Doctor, Registration, RegStatus, MedicalRecord, Patient, Examination, Payment, PaymentType, Prescription, ExamResult
from app.schemas.hospital import MedicalRecordCreate
from app.schemas.hospital import ExaminationCreate
import random

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
    # 在开始办理时创建挂号缴费（挂号费）——金额等于挂号单的 fee
    try:
        pay_stmt = select(Payment).where(
            Payment.type == PaymentType.REGISTRATION,
            Payment.patient_id == registration.patient_id,
            Payment.amount == registration.fee
        )
        existing = (await session.execute(pay_stmt)).scalars().first()
    except Exception:
        existing = None

    if not existing:
        p = Payment(type=PaymentType.REGISTRATION, amount=registration.fee, patient_id=registration.patient_id)
        session.add(p)
        await session.commit()
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