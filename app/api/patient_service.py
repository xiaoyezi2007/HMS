from fastapi import APIRouter, Depends, HTTPException
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
    MedicalRecord,
)
from app.models.hospital import (
    Payment,
    Prescription,
    Examination,
    PrescriptionDetail,
    Medicine,
)
from app.models.user import UserAccount, UserRole
from app.schemas.hospital import PatientCreate, RegistrationCreate

router = APIRouter()


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

    reg.status = RegStatus.CANCELLED
    session.add(reg)
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
                "status": p.status,
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

    # 标记为已缴费
    payment.status = '已缴费'
    session.add(payment)

    # 若这是处方缴费，则同步更新处方状态
    if payment.pres_id:
        pres = await session.get(Prescription, payment.pres_id)
        if pres:
            pres.status = '已缴费'
            session.add(pres)

    await session.commit()
    await session.refresh(payment)
    return {"message": "已缴费", "payment": {
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