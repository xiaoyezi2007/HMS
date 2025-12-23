from datetime import datetime, timedelta, date
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import List

from app.core.config import get_session
# --- 修改点：从 deps 导入 ---
from app.api.deps import get_current_user_phone, get_current_user
from app.models.hospital import (
    Patient,
    Department,
    Doctor,
    Registration,
    RegStatus,
    RegType,
    MedicalRecord,
    PaymentType,
)
from app.models.hospital import (
    Payment,
    Prescription,
    Examination,
    PrescriptionDetail,
    Medicine,
    Hospitalization,
    Ward,
)
from app.models.user import UserAccount, UserRole
from app.schemas.hospital import PatientCreate, RegistrationCreate
from app.services.billing import (
    DEFAULT_HOSPITAL_HOURLY_RATE,
    compute_hospitalization_bill,
)

router = APIRouter()


async def _apply_expired_registrations_for_patient(session: AsyncSession, patient_id: int) -> None:
    """Mark overdue WAITING registrations as EXPIRED and sync registration fee payment status.

    Rules:
    - If today > visit_date and registration is WAITING, set registration.status = 已过期
    - For an expired registration:
        - if its registration fee payment is not 已缴费, set payment.status = 已取消
        - if 已缴费, keep 已缴费 (no refund)
    """

    today = date.today()
    stmt = select(Registration).where(
        Registration.patient_id == patient_id,
        Registration.status == RegStatus.WAITING,
        Registration.visit_date < today,
    )
    regs = (await session.execute(stmt)).scalars().all()
    if not regs:
        return

    for reg in regs:
        with session.no_autoflush:
            pay_stmt = (
                select(Payment)
                .where(Payment.patient_id == patient_id)
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
            payment = (await session.execute(pay_stmt)).scalars().first()

            # Backward compatibility: older rows may not have reg_id filled.
            if not payment:
                window_start = reg.reg_date - timedelta(hours=2)
                window_end = reg.reg_date + timedelta(hours=2)
                pay_stmt2 = (
                    select(Payment)
                    .where(Payment.patient_id == patient_id)
                    .where(
                        or_(
                            Payment.type == PaymentType.REGISTRATION,
                            Payment.type == "挂号费",
                            Payment.type == "REGISTRATION",
                        )
                    )
                    .where(Payment.pres_id.is_(None))
                    .where(Payment.exam_id.is_(None))
                    .where(Payment.hosp_id.is_(None))
                    .where(Payment.time >= window_start)
                    .where(Payment.time <= window_end)
                    .order_by(Payment.time.desc(), Payment.payment_id.desc())
                )
                payment = (await session.execute(pay_stmt2)).scalars().first()

        reg.status = RegStatus.EXPIRED
        session.add(reg)

        if payment and getattr(payment, "status", "未缴费") != "已缴费":
            payment.status = "已取消"
            session.add(payment)

    await session.commit()


# --- 接口 1: 查询患者档案 ---
@router.get("/profile", response_model=Patient)
async def get_patient_profile(
        phone: str = Depends(get_current_user_phone),
        session: AsyncSession = Depends(get_session)
):
    stmt = select(Patient).where(Patient.phone == phone)
    patient = (await session.execute(stmt)).scalars().first()
    if not patient:
        raise HTTPException(status_code=404, detail="未找到档案")
    return patient


# --- 新：患者自查（基于登录 Token） ---
@router.get("/medical_records", response_model=List[MedicalRecord])
async def get_my_medical_records(
    phone: str = Depends(get_current_user_phone),
    session: AsyncSession = Depends(get_session)
):
    # 通过登录手机号找到 Patient，再查病历
    stmt = select(Patient).where(Patient.phone == phone)
    patient = (await session.execute(stmt)).scalars().first()
    if not patient:
        raise HTTPException(status_code=400, detail="请先完善个人信息档案")

    reg_stmt = select(Registration.reg_id).where(Registration.patient_id == patient.patient_id)
    reg_ids = (await session.execute(reg_stmt)).scalars().all()
    if not reg_ids:
        return []

    rec_stmt = select(MedicalRecord).where(MedicalRecord.reg_id.in_(reg_ids))
    records = (await session.execute(rec_stmt)).scalars().all()
    return records


# --- 新：按 patient_id 查询（仅限医生或管理员） ---
@router.get("/patients/{patient_id}/medical_records", response_model=List[MedicalRecord])
async def get_patient_medical_records_by_id(
    patient_id: int,
    current_user: UserAccount = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # 权限校验：仅允许管理员或医生查询
    if current_user.role not in (UserRole.ADMIN, UserRole.DOCTOR):
        raise HTTPException(status_code=403, detail="需要医生或管理员权限")

    reg_stmt = select(Registration.reg_id).where(Registration.patient_id == patient_id)
    reg_ids = (await session.execute(reg_stmt)).scalars().all()
    if not reg_ids:
        return []

    stmt = select(MedicalRecord).where(MedicalRecord.reg_id.in_(reg_ids))
    records = (await session.execute(stmt)).scalars().all()
    return records


# --- 新：按 patient_id 获取患者基本信息（仅限医生或管理员） ---
@router.get("/patients/{patient_id}", response_model=Patient)
async def get_patient_by_id(
    patient_id: int,
    current_user: UserAccount = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    if current_user.role not in (UserRole.ADMIN, UserRole.DOCTOR):
        raise HTTPException(status_code=403, detail="需要医生或管理员权限")

    stmt = select(Patient).where(Patient.patient_id == patient_id)
    patient = (await session.execute(stmt)).scalars().first()
    if not patient:
        raise HTTPException(status_code=404, detail="患者不存在")
    return patient


# --- 接口 2: 完善/创建患者档案（存在时即更新） ---
@router.post("/profile", response_model=Patient)
async def create_or_update_patient_profile(
        profile: PatientCreate,
        phone: str = Depends(get_current_user_phone),  # 直接使用导入的函数
        session: AsyncSession = Depends(get_session)
):
    stmt = select(Patient).where(Patient.phone == phone)
    existing = (await session.execute(stmt)).scalars().first()
    if existing:
        for field, value in profile.dict().items():
            setattr(existing, field, value)
        await session.commit()
        await session.refresh(existing)
        return existing

    patient = Patient(phone=phone, **profile.dict())
    session.add(patient)
    await session.commit()
    await session.refresh(patient)
    return patient


# --- 接口 3: 获取所有科室 ---
@router.get("/departments", response_model=List[Department])
async def get_departments(session: AsyncSession = Depends(get_session)):
    stmt = select(Department)
    result = await session.execute(stmt)
    return result.scalars().all()


# --- 接口 4: 获取医生 ---
@router.get("/doctors/{dept_id}", response_model=List[Doctor])
async def get_doctors_by_dept(dept_id: int, session: AsyncSession = Depends(get_session)):
    # 只返回启用状态的医生
    stmt = (
        select(Doctor)
        .join(UserAccount, Doctor.phone == UserAccount.phone)
        .where(Doctor.dept_id == dept_id)
        .where(UserAccount.status == "启用")
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.get("/doctors/id/{doctor_id}", response_model=Doctor)
async def get_doctor_by_id(doctor_id: int, session: AsyncSession = Depends(get_session)):
    stmt = select(Doctor).where(Doctor.doctor_id == doctor_id)
    doctor = (await session.execute(stmt)).scalars().first()
    if not doctor:
        raise HTTPException(status_code=404, detail="医生不存在")
    return doctor


# --- 接口 5: 挂号 ---
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

    # 规则：患者同一时间只能有一个“未完成”的挂号（排队中/就诊中）。
    active_stmt = select(Registration.reg_id).where(
        Registration.patient_id == patient.patient_id,
        Registration.status.in_([RegStatus.WAITING, RegStatus.IN_PROGRESS])
    )
    active_reg_id = (await session.execute(active_stmt)).scalars().first()
    if active_reg_id:
        raise HTTPException(status_code=400, detail="您还有未完成的挂号，请在上一次挂号完成后再进行下一次挂号")

    visit_date = getattr(reg_in, "visit_date", None) or datetime.now().date()

    # 挂号限额：同一医生当日，专家号最多30个，普通号最多50个（不含已取消）
    limit = 30 if reg_in.reg_type in (RegType.EXPERT, RegType.EXPERT.value, "专家号") else 50
    quota_stmt = (
        select(func.count())
        .where(Registration.doctor_id == reg_in.doctor_id)
        .where(Registration.visit_date == visit_date)
        .where(Registration.reg_type == reg_in.reg_type)
        .where(Registration.status != RegStatus.CANCELLED)
    )
    current_count = (await session.execute(quota_stmt)).scalar_one() or 0
    if current_count >= limit:
        raise HTTPException(status_code=400, detail="该医生当天挂号已满")

    fee = 50.0 if reg_in.reg_type in (RegType.EXPERT, RegType.EXPERT.value, "专家号") else 10.0

    new_reg = Registration(
        patient_id=patient.patient_id,
        doctor_id=reg_in.doctor_id,
        reg_type=reg_in.reg_type,
        visit_date=visit_date,
        symptoms=getattr(reg_in, "symptoms", None),
        fee=fee,
        status=RegStatus.WAITING
    )

    # 挂号时就生成一条“待缴费”的挂号费记录
    session.add(new_reg)
    await session.flush()
    session.add(
        Payment(
            type=PaymentType.REGISTRATION,
            amount=fee,
            patient_id=patient.patient_id,
            status="未缴费",
            time=new_reg.reg_date,
            reg_id=new_reg.reg_id,
        )
    )

    await session.commit()
    await session.refresh(new_reg)
    return new_reg


@router.post("/registrations/{reg_id}/cancel")
async def cancel_registration(
    reg_id: int,
    phone: str = Depends(get_current_user_phone),
    session: AsyncSession = Depends(get_session)
):
    # 只允许在医生开始办理前由患者取消
    stmt = select(Patient).where(Patient.phone == phone)
    patient = (await session.execute(stmt)).scalars().first()
    if not patient:
        raise HTTPException(status_code=400, detail="请先完善个人信息档案")

    reg = await session.get(Registration, reg_id)
    if not reg:
        raise HTTPException(status_code=404, detail="挂号单不存在")
    if reg.patient_id != patient.patient_id:
        raise HTTPException(status_code=403, detail="无权取消该挂号")
    if reg.status != RegStatus.WAITING:
        raise HTTPException(status_code=400, detail="只有未开始的挂号可以取消")

    # 找到最新的“挂号费”缴费记录：
    # 由于系统限制同一时间只有一个未完成挂号，因此取最新一条即可。
    # 优先按 reg_id 精确锁定对应挂号费
    pay_stmt_exact = (
        select(Payment)
        .where(Payment.patient_id == patient.patient_id)
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
    payment = (await session.execute(pay_stmt_exact)).scalars().first()

    # 兼容旧数据：按“本次挂号时间窗口”锁定对应挂号费（避免历史遗留的挂号费误匹配）
    window_start = reg.reg_date - timedelta(hours=2)
    window_end = reg.reg_date + timedelta(hours=2)
    if not payment:
        pay_stmt = (
            select(Payment)
            .where(Payment.patient_id == patient.patient_id)
            .where(
                or_(
                    Payment.type == PaymentType.REGISTRATION,
                    Payment.type == "挂号费",
                    Payment.type == "REGISTRATION",
                )
            )
            .where(Payment.pres_id.is_(None))
            .where(Payment.exam_id.is_(None))
            .where(Payment.hosp_id.is_(None))
            .where(Payment.time >= window_start)
            .where(Payment.time <= window_end)
            .order_by(Payment.time.desc(), Payment.payment_id.desc())
        )
        payment = (await session.execute(pay_stmt)).scalars().first()

    # 若窗口内没找到，再退回到“最新挂号费”匹配
    if not payment:
        pay_stmt_latest = (
            select(Payment)
            .where(Payment.patient_id == patient.patient_id)
            .where(
                or_(
                    Payment.type == PaymentType.REGISTRATION,
                    Payment.type == "挂号费",
                    Payment.type == "REGISTRATION",
                )
            )
            .where(Payment.pres_id.is_(None))
            .where(Payment.exam_id.is_(None))
            .where(Payment.hosp_id.is_(None))
            .order_by(Payment.time.desc(), Payment.payment_id.desc())
        )
        payment = (await session.execute(pay_stmt_latest)).scalars().first()

    # 兜底：若由于历史数据/字段异常没匹配到，则按金额匹配最近一条挂号费
    if not payment:
        pay_stmt2 = (
            select(Payment)
            .where(Payment.patient_id == patient.patient_id)
            .where(
                or_(
                    Payment.type == PaymentType.REGISTRATION,
                    Payment.type == "挂号费",
                    Payment.type == "REGISTRATION",
                )
            )
            .where(Payment.amount == reg.fee)
            .where(or_(Payment.status == '未缴费', Payment.status == '已缴费', Payment.status == '待退费'))
            .order_by(Payment.time.desc(), Payment.payment_id.desc())
        )
        payment = (await session.execute(pay_stmt2)).scalars().first()

    reg.status = RegStatus.CANCELLED
    session.add(reg)

    # 取消挂号：
    # - 若挂号费未缴费：标记为“已取消”（保留记录，但不可再缴费）
    # - 若已缴费：标记为“待退费”，前端显示退费按钮 + 铃铛提醒
    if payment:
        if getattr(payment, "status", "未缴费") == "已缴费":
            payment.status = "待退费"
            session.add(payment)
        else:
            payment.status = "已取消"
            session.add(payment)

    await session.commit()
    await session.refresh(reg)
    return {"message": "挂号已取消", "registration": reg}


# --- 新：查询当前患者的所有挂号记录 ---
@router.get("/registrations", response_model=List[Registration])
async def get_my_registrations(
    phone: str = Depends(get_current_user_phone),
    session: AsyncSession = Depends(get_session)
):
    try:
        stmt = select(Patient).where(Patient.phone == phone)
        patient = (await session.execute(stmt)).scalars().first()
        if not patient:
            raise HTTPException(status_code=400, detail="请先完善个人信息档案")

        reg_stmt = select(Registration).where(Registration.patient_id == patient.patient_id)
        await _apply_expired_registrations_for_patient(session, patient.patient_id)
        result = await session.execute(reg_stmt)
        return result.scalars().all()
    except HTTPException:
        # re-raise known HTTP exceptions
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Return a clearer error message to front-end for debugging
        raise HTTPException(status_code=500, detail=f"查询挂号列表异常: {str(e)}")



@router.get("/registrations/{reg_id}/detail")
async def get_registration_detail(
    reg_id: int,
    phone: str = Depends(get_current_user_phone),
    session: AsyncSession = Depends(get_session)
):
    # ensure the registration belongs to the current logged-in patient
    stmt = select(Patient).where(Patient.phone == phone)
    patient = (await session.execute(stmt)).scalars().first()
    if not patient:
        raise HTTPException(status_code=400, detail="请先完善个人信息档案")

    await _apply_expired_registrations_for_patient(session, patient.patient_id)

    reg_stmt = select(Registration).where(Registration.reg_id == reg_id)
    registration = (await session.execute(reg_stmt)).scalars().first()
    if not registration:
        raise HTTPException(status_code=404, detail="挂号单不存在")
    if registration.patient_id != patient.patient_id:
        raise HTTPException(status_code=403, detail="无权查看该挂号")

    # fetch medical record if exists
    rec_stmt = select(MedicalRecord).where(MedicalRecord.reg_id == reg_id)
    record = (await session.execute(rec_stmt)).scalars().first()

    # fetch prescriptions linked to this record (if record exists)
    pres_list = []
    if record:
        from app.models.hospital import Prescription, PrescriptionDetail, Medicine
        pres_stmt = select(Prescription).where(Prescription.record_id == record.record_id)
        pres = (await session.execute(pres_stmt)).scalars().all()
        for p in pres:
            # fetch details
            details_stmt = select(PrescriptionDetail).where(PrescriptionDetail.pres_id == p.pres_id)
            details = (await session.execute(details_stmt)).scalars().all()
            # enrich with medicine info where available
            enriched = []
            for d in details:
                med = await session.get(Medicine, d.medicine_id)
                enriched.append({
                    "detail_id": d.detail_id,
                    "medicine_id": d.medicine_id,
                    "medicine_name": med.name if med else None,
                    "quantity": d.quantity,
                    "usage": d.usage
                })
            pres_list.append({
                "pres_id": p.pres_id,
                "create_time": p.create_time,
                "total_amount": p.total_amount,
                "details": enriched
            })

    # fetch examinations if record exists
    exams_list = []
    if record:
        from app.models.hospital import Examination
        exam_stmt = select(Examination).where(Examination.record_id == record.record_id)
        exams = (await session.execute(exam_stmt)).scalars().all()
        for e in exams:
            exams_list.append({
                "exam_id": e.exam_id,
                "type": e.type,
                "result": e.result,
                "date": e.date,
                "record_id": e.record_id,
                "reg_id": record.reg_id
            })

    return {"registration": registration, "record": record, "prescriptions": pres_list, "exams": exams_list, "admissions": []}


# --- 新：查询当前患者的缴费记录 ---
@router.get("/payments")
async def get_my_payments(
    phone: str = Depends(get_current_user_phone),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Patient).where(Patient.phone == phone)
    patient = (await session.execute(stmt)).scalars().first()
    if not patient:
        raise HTTPException(status_code=400, detail="请先完善个人信息档案")

    # Ensure overdue registrations are marked expired and registration fee payment status updated.
    await _apply_expired_registrations_for_patient(session, patient.patient_id)

    pay_stmt = select(Payment).where(Payment.patient_id == patient.patient_id)
    result = await session.execute(pay_stmt)
    pays = result.scalars().all()
    out = []
    for p in pays:
        entry = {
            "payment_id": p.payment_id,
            "type": p.type.value if hasattr(p.type, 'value') else p.type,
            "amount": p.amount,
            "time": p.time,
            "patient_id": p.patient_id,
            "reg_id": getattr(p, 'reg_id', None),
            "pres_id": p.pres_id,
            "exam_id": p.exam_id,
            "hosp_id": p.hosp_id,
            "status": getattr(p, 'status', '未缴费')
        }

        if p.exam_id:
            exam = await session.get(Examination, p.exam_id)
            entry["exam_info"] = {
                "exam_id": exam.exam_id,
                "type": exam.type,
                "result": exam.result,
                "date": exam.date
            } if exam else None

        if p.pres_id:
            pres = await session.get(Prescription, p.pres_id)
            details = []
            if pres:
                detail_stmt = select(PrescriptionDetail).where(PrescriptionDetail.pres_id == pres.pres_id)
                for ds in (await session.execute(detail_stmt)).scalars().all():
                    med = await session.get(Medicine, ds.medicine_id)
                    details.append({
                        "medicine_id": ds.medicine_id,
                        "medicine_name": med.name if med else None,
                        "quantity": ds.quantity,
                        "usage": ds.usage
                    })
            entry["prescription_info"] = {
                "pres_id": pres.pres_id if pres else None,
                "total_amount": pres.total_amount if pres else None,
                "details": details
            }

        if p.hosp_id:
            hosp = await session.get(Hospitalization, p.hosp_id)
            if hosp:
                ward = await session.get(Ward, hosp.ward_id) if hosp.ward_id else None
                reference_out = hosp.out_date or datetime.now()
                duration_hours = max((reference_out - hosp.in_date).total_seconds() / 3600, 0.0)
                entry["hospitalization_info"] = {
                    "hosp_id": hosp.hosp_id,
                    "ward_id": hosp.ward_id,
                    "ward_type": ward.type if ward else None,
                    "status": hosp.status,
                    "in_date": hosp.in_date,
                    "out_date": hosp.out_date,
                    "duration_hours": duration_hours,
                    "duration_days": round(duration_hours / 24, 2)
                }
                entry["hospitalization_bill"] = await compute_hospitalization_bill(
                    session,
                    hosp,
                    DEFAULT_HOSPITAL_HOURLY_RATE,
                )

        out.append(entry)
    return out


# --- 新：对某项缴费立即完成缴费 ---
@router.post("/payments/{payment_id}/pay")
async def pay_payment(
    payment_id: int,
    phone: str = Depends(get_current_user_phone),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Patient).where(Patient.phone == phone)
    patient = (await session.execute(stmt)).scalars().first()
    if not patient:
        raise HTTPException(status_code=400, detail="请先完善个人信息档案")

    payment = await session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="缴费记录不存在")
    if payment.patient_id != patient.patient_id:
        raise HTTPException(status_code=403, detail="无权操作此缴费记录")

    if getattr(payment, 'status', None) == '已缴费':
        return {"message": "该项已缴费", "payment_id": payment.payment_id}

    if getattr(payment, 'status', None) in ('已取消', '待退费', '已退费'):
        raise HTTPException(status_code=400, detail="该项不可缴费")

    # 标记为已缴费
    payment.status = '已缴费'
    session.add(payment)

    await session.commit()
    await session.refresh(payment)
    return {"message": "已缴费", "payment": {
        "payment_id": payment.payment_id,
        "status": payment.status
    }}


@router.post("/payments/{payment_id}/refund")
async def refund_payment(
    payment_id: int,
    phone: str = Depends(get_current_user_phone),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Patient).where(Patient.phone == phone)
    patient = (await session.execute(stmt)).scalars().first()
    if not patient:
        raise HTTPException(status_code=400, detail="请先完善个人信息档案")

    payment = await session.get(Payment, payment_id)
    if not payment:
        raise HTTPException(status_code=404, detail="缴费记录不存在")
    if payment.patient_id != patient.patient_id:
        raise HTTPException(status_code=403, detail="无权操作此缴费记录")

    if payment.type != PaymentType.REGISTRATION:
        raise HTTPException(status_code=400, detail="仅挂号费支持退费")

    if getattr(payment, 'status', None) != '待退费':
        raise HTTPException(status_code=400, detail="该项当前不可退费")

    payment.status = '已退费'
    session.add(payment)
    await session.commit()
    await session.refresh(payment)
    return {"message": "已退费", "payment": {
        "payment_id": payment.payment_id,
        "status": payment.status
    }}


@router.get("/examinations")
async def get_my_examinations(
    phone: str = Depends(get_current_user_phone),
    session: AsyncSession = Depends(get_session)
):
    # 通过登录手机号找到 Patient，再查该患者所有挂号对应的病历的检查记录
    stmt = select(Patient).where(Patient.phone == phone)
    patient = (await session.execute(stmt)).scalars().first()
    if not patient:
        raise HTTPException(status_code=400, detail="请先完善个人信息档案")

    # 查找该患者的所有挂号 id
    reg_stmt = select(Registration.reg_id).where(Registration.patient_id == patient.patient_id)
    reg_ids = (await session.execute(reg_stmt)).scalars().all()
    if not reg_ids:
        return []

    # 找到对应的病历 id 列表
    rec_stmt = select(MedicalRecord.record_id).where(MedicalRecord.reg_id.in_(reg_ids))
    record_ids = (await session.execute(rec_stmt)).scalars().all()
    if not record_ids:
        return []

    from app.models.hospital import Examination
    exam_stmt = select(Examination).where(Examination.record_id.in_(record_ids))
    exams = (await session.execute(exam_stmt)).scalars().all()

    # 需要把每个 exam 的 record_id 对应到它的 reg_id（挂号 id）
    recs_stmt = select(MedicalRecord).where(MedicalRecord.record_id.in_(record_ids))
    recs = (await session.execute(recs_stmt)).scalars().all()
    rec_map = {r.record_id: r.reg_id for r in recs}

    out = []
    for e in exams:
        out.append({
            "exam_id": e.exam_id,
            "type": e.type,
            "result": e.result,
            "date": e.date,
            "record_id": e.record_id,
            "reg_id": rec_map.get(e.record_id)
        })

    return out