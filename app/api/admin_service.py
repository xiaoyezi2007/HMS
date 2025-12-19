from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.api.deps import get_current_admin_user
from app.core.config import get_session
from app.core.security import get_password_hash
from app.models.user import UserAccount, UserRole
from app.models.hospital import Doctor, Nurse, Department, Ward, Gender, Payment, Patient
from app.schemas.user import StaffAccountCreate, UserAccountSafe
from app.schemas.hospital import (
    DoctorTitleUpdate,
    NurseHeadUpdate,
    ALLOWED_DOCTOR_TITLES,
    DepartmentCreate,
    WardCreate,
)

router = APIRouter()

MANAGEABLE_ROLES = {UserRole.DOCTOR, UserRole.NURSE, UserRole.PHARMACIST}
DEFAULT_PASSWORD = "123456"


def _to_safe(account: UserAccount) -> UserAccountSafe:
    return UserAccountSafe(
        phone=account.phone,
        username=account.username,
        role=account.role,
        status=account.status,
        register_time=account.register_time
    )


@router.get("/admin/accounts", response_model=List[UserAccountSafe])
async def list_staff_accounts(
    role: Optional[UserRole] = None,
    _: UserAccount = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    role_filter = role
    if role_filter and role_filter not in MANAGEABLE_ROLES:
        raise HTTPException(status_code=400, detail="只能查看医生/护士/药师账号")

    stmt = select(UserAccount).where(UserAccount.role.in_(list(MANAGEABLE_ROLES)))
    if role_filter:
        stmt = stmt.where(UserAccount.role == role_filter)

    result = await session.execute(stmt)
    accounts = result.scalars().all()
    return [_to_safe(item) for item in accounts]


@router.post("/admin/accounts", response_model=UserAccountSafe, status_code=status.HTTP_201_CREATED)
async def create_staff_account(
    payload: StaffAccountCreate,
    _: UserAccount = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    if payload.role not in MANAGEABLE_ROLES:
        raise HTTPException(status_code=400, detail="仅能创建医生/护士/药师账号")

    if payload.role == UserRole.DOCTOR:
        if not payload.dept_id:
            raise HTTPException(status_code=400, detail="医生账号必须指定所属科室")
        if not payload.doctor_name:
            raise HTTPException(status_code=400, detail="请提供医生姓名")
        if not payload.doctor_gender:
            raise HTTPException(status_code=400, detail="请提供医生性别")
        if not payload.doctor_title:
            raise HTTPException(status_code=400, detail="请提供医生级别")

        doctor_title = "专家医师" if payload.doctor_title == "主治医师" else payload.doctor_title
        if doctor_title not in ALLOWED_DOCTOR_TITLES:
            raise HTTPException(status_code=400, detail="医生级别仅支持专家医师或普通医师")

        dept = (await session.execute(select(Department).where(Department.dept_id == payload.dept_id))).scalars().first()
        if not dept:
            raise HTTPException(status_code=404, detail="指定的科室不存在")

    if payload.role == UserRole.NURSE:
        if not payload.nurse_name:
            raise HTTPException(status_code=400, detail="请提供护士姓名")
        if not payload.nurse_gender:
            raise HTTPException(status_code=400, detail="请提供护士性别")

    phone_exists = (await session.execute(select(UserAccount).where(UserAccount.phone == payload.phone))).scalars().first()
    if phone_exists:
        raise HTTPException(status_code=400, detail="该手机号已被注册")

    username_exists = (await session.execute(select(UserAccount).where(UserAccount.username == payload.username))).scalars().first()
    if username_exists:
        raise HTTPException(status_code=400, detail="该用户名已被占用")

    account = UserAccount(
        phone=payload.phone,
        username=payload.username,
        role=payload.role,
        password_hash=get_password_hash(DEFAULT_PASSWORD),
        status="启用"
    )

    session.add(account)
    await session.commit()
    await session.refresh(account)

    if payload.role == UserRole.DOCTOR:
        doctor = (await session.execute(select(Doctor).where(Doctor.phone == payload.phone))).scalars().first()
        gender_value = payload.doctor_gender if isinstance(payload.doctor_gender, Gender) else Gender(payload.doctor_gender)
        if doctor:
            doctor.name = payload.doctor_name
            doctor.gender = gender_value
            doctor.title = doctor_title
            doctor.dept_id = payload.dept_id
            session.add(doctor)
        else:
            doctor = Doctor(
                name=payload.doctor_name,
                gender=gender_value,
                title=doctor_title,
                phone=payload.phone,
                dept_id=payload.dept_id
            )
            session.add(doctor)
        await session.commit()
        await session.refresh(doctor)

    if payload.role == UserRole.NURSE:
        nurse = (await session.execute(select(Nurse).where(Nurse.phone == payload.phone))).scalars().first()
        gender_value = payload.nurse_gender if isinstance(payload.nurse_gender, Gender) else Gender(payload.nurse_gender)
        if nurse:
            nurse.name = payload.nurse_name
            nurse.gender = gender_value
            session.add(nurse)
        else:
            nurse = Nurse(
                name=payload.nurse_name,
                gender=gender_value,
                phone=payload.phone,
                is_head_nurse=False
            )
            session.add(nurse)
        await session.commit()
        await session.refresh(nurse)

    return _to_safe(account)


@router.delete("/admin/accounts/{phone}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_staff_account(
    phone: str,
    _: UserAccount = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(UserAccount).where(UserAccount.phone == phone)
    account = (await session.execute(stmt)).scalars().first()
    if not account or account.role not in MANAGEABLE_ROLES:
        raise HTTPException(status_code=404, detail="未找到可删除的医生/护士/药师账号")

    account.status = "禁用"
    session.add(account)
    await session.commit()


@router.get("/admin/doctors")
async def list_doctors(
    _: UserAccount = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    # 只返回启用状态的医生账号，并关联科室名称
    stmt = (
        select(Doctor, Department.dept_name)
        .join(UserAccount, Doctor.phone == UserAccount.phone)
        .outerjoin(Department, Doctor.dept_id == Department.dept_id)
        .where(UserAccount.status == "启用")
    )
    result = await session.execute(stmt)
    doctors_with_dept = []
    for doctor, dept_name in result.all():
        doctor_dict = {
            "doctor_id": doctor.doctor_id,
            "name": doctor.name,
            "gender": doctor.gender,
            "title": doctor.title,
            "phone": doctor.phone,
            "dept_id": doctor.dept_id,
            "dept_name": dept_name
        }
        doctors_with_dept.append(doctor_dict)
    return doctors_with_dept


@router.patch("/admin/doctors/{doctor_id}/title", response_model=Doctor)
async def update_doctor_title(
    doctor_id: int,
    payload: DoctorTitleUpdate,
    _: UserAccount = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    # payload.title 已在 schema validator 中做了兼容与归一化（主治医师 -> 专家医师）
    if payload.title not in ALLOWED_DOCTOR_TITLES:
        raise HTTPException(status_code=400, detail="医生级别仅支持专家医师或普通医师")

    doctor = (await session.execute(select(Doctor).where(Doctor.doctor_id == doctor_id))).scalars().first()
    if not doctor:
        raise HTTPException(status_code=404, detail="医生不存在")

    doctor.title = payload.title
    session.add(doctor)
    await session.commit()
    await session.refresh(doctor)
    return doctor


@router.get("/admin/nurses", response_model=List[Nurse])
async def list_nurses(
    _: UserAccount = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    # 只返回启用状态的护士账号
    stmt = (
        select(Nurse)
        .join(UserAccount, Nurse.phone == UserAccount.phone)
        .where(UserAccount.status == "启用")
    )
    result = await session.execute(stmt)
    return result.scalars().all()


@router.patch("/admin/nurses/{nurse_id}/head", response_model=Nurse)
async def update_nurse_head_status(
    nurse_id: int,
    payload: NurseHeadUpdate,
    _: UserAccount = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    nurse = (await session.execute(select(Nurse).where(Nurse.nurse_id == nurse_id))).scalars().first()
    if not nurse:
        raise HTTPException(status_code=404, detail="护士不存在")

    nurse.is_head_nurse = payload.is_head_nurse
    session.add(nurse)
    await session.commit()
    await session.refresh(nurse)
    return nurse


@router.get("/admin/revenue")
async def get_revenue_summary(
    _: UserAccount = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    paid_filter = Payment.status == "已缴费"

    total_stmt = select(
        func.coalesce(func.sum(Payment.amount), 0).label("total_amount"),
        func.count(Payment.payment_id).label("paid_count")
    ).where(paid_filter)
    total_row = (await session.execute(total_stmt)).first()
    total_amount = float(total_row.total_amount) if total_row and total_row.total_amount is not None else 0.0
    paid_count = total_row.paid_count if total_row else 0

    type_stmt = (
        select(
            Payment.type,
            func.coalesce(func.sum(Payment.amount), 0).label("amount"),
            func.count(Payment.payment_id).label("count")
        )
        .where(paid_filter)
        .group_by(Payment.type)
    )
    type_rows = await session.execute(type_stmt)
    by_type = []
    for row in type_rows:
        entry_type = row.type.value if hasattr(row.type, "value") else row.type
        by_type.append({
            "type": entry_type,
            "amount": float(row.amount or 0.0),
            "count": row.count
        })

    record_stmt = (
        select(Payment, Patient.name, Patient.phone)
        .join(Patient, Payment.patient_id == Patient.patient_id)
        .where(paid_filter)
        .order_by(Payment.time.desc())
        .limit(200)
    )
    record_rows = await session.execute(record_stmt)
    records = []
    for payment, patient_name, patient_phone in record_rows.all():
        records.append({
            "payment_id": payment.payment_id,
            "type": payment.type.value if hasattr(payment.type, "value") else payment.type,
            "amount": payment.amount,
            "time": payment.time,
            "patient_id": payment.patient_id,
            "patient_name": patient_name,
            "patient_phone": patient_phone,
            "pres_id": payment.pres_id,
            "exam_id": payment.exam_id,
            "hosp_id": payment.hosp_id
        })

    return {
        "total_amount": total_amount,
        "paid_count": paid_count,
        "by_type": by_type,
        "records": records
    }


@router.post("/admin/departments", response_model=Department, status_code=status.HTTP_201_CREATED)
async def create_department(
    payload: DepartmentCreate,
    _: UserAccount = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    existing = (await session.execute(select(Department).where(Department.dept_name == payload.dept_name))).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="科室名称已存在")

    dept = Department(dept_name=payload.dept_name, telephone=payload.telephone)
    session.add(dept)
    await session.commit()
    await session.refresh(dept)
    return dept


@router.get("/admin/wards")
async def list_wards(
    _: UserAccount = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    stmt = select(Ward, Department.dept_name).join(Department, Ward.dept_id == Department.dept_id)
    rows = await session.execute(stmt)
    result = []
    for ward, dept_name in rows.all():
        result.append({
            "ward_id": ward.ward_id,
            "bed_count": ward.bed_count,
            "type": ward.type,
            "dept_id": ward.dept_id,
            "dept_name": dept_name
        })
    return result


@router.post("/admin/wards", status_code=status.HTTP_201_CREATED)
async def create_ward(
    payload: WardCreate,
    _: UserAccount = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    dept = await session.get(Department, payload.dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="科室不存在")
    if payload.bed_count <= 0:
        raise HTTPException(status_code=400, detail="床位数必须大于 0")
    if not payload.type.strip():
        raise HTTPException(status_code=400, detail="病房类型不能为空")

    ward = Ward(dept_id=payload.dept_id, bed_count=payload.bed_count, type=payload.type.strip())
    session.add(ward)
    await session.commit()
    await session.refresh(ward)
    return {
        "ward_id": ward.ward_id,
        "bed_count": ward.bed_count,
        "type": ward.type,
        "dept_id": ward.dept_id,
        "dept_name": dept.dept_name
    }