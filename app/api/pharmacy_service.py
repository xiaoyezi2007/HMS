from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from typing import Dict, List
from datetime import datetime, timedelta
import math

from app.core.config import get_session
from app.api.deps import get_current_user, get_current_user_phone
from app.models.hospital import Doctor, Medicine, Prescription, PrescriptionDetail, MedicalRecord, Registration, RegStatus
from app.models.user import UserAccount, UserRole
from app.schemas.pharmacy import (
    PrescriptionCreate,
    PrescriptionRead,
    MedicinePurchase,
    MedicineCreate,
    MedicineInventory,
)

router = APIRouter()

USAGE_WINDOW_DAYS = 30
PLANNING_HORIZON_DAYS = 7


def _build_inventory_view(med: Medicine, usage_map: Dict[int, int]) -> MedicineInventory:
    usage_30d = int(usage_map.get(med.medicine_id, 0) or 0)
    avg_daily = usage_30d / USAGE_WINDOW_DAYS if usage_30d else 0.0
    expected_week_usage = math.ceil(avg_daily * PLANNING_HORIZON_DAYS)
    suggested_restock = max(expected_week_usage - med.stock, 0)
    return MedicineInventory(
        medicine_id=med.medicine_id,
        name=med.name,
        price=med.price,
        stock=med.stock,
        unit=med.unit,
        usage_30d=usage_30d,
        avg_daily_usage=round(avg_daily, 2),
        expected_week_usage=expected_week_usage,
        suggested_restock=suggested_restock,
        needs_restock=suggested_restock > 0,
    )


async def _load_usage_map(session: AsyncSession) -> Dict[int, int]:
    cutoff = datetime.now() - timedelta(days=USAGE_WINDOW_DAYS)
    stmt = (
        select(
            PrescriptionDetail.medicine_id,
            func.coalesce(func.sum(PrescriptionDetail.quantity), 0),
        )
        .join(Prescription, PrescriptionDetail.pres_id == Prescription.pres_id)
        .where(Prescription.create_time >= cutoff)
        .group_by(PrescriptionDetail.medicine_id)
    )
    rows = await session.execute(stmt)
    return {medicine_id: int(total or 0) for medicine_id, total in rows.all()}


# 简单的医生验证
async def get_current_doctor(
        phone: str = Depends(get_current_user_phone),
        session: AsyncSession = Depends(get_session)
) -> Doctor:
    doc = (await session.execute(select(Doctor).where(Doctor.phone == phone))).scalars().first()
    if not doc:
        raise HTTPException(status_code=403, detail="无权操作")
    return doc


async def get_current_pharmacist(
    current_user: UserAccount = Depends(get_current_user)
) -> UserAccount:
    if current_user.role != UserRole.PHARMACIST:
        raise HTTPException(status_code=403, detail="需要药师权限")
    return current_user


@router.get("/medicines", response_model=List[MedicineInventory])
async def get_medicines(session: AsyncSession = Depends(get_session)):
    meds = (await session.execute(select(Medicine))).scalars().all()
    usage_map = await _load_usage_map(session)
    return [_build_inventory_view(med, usage_map) for med in meds]


@router.post("/medicines/replenish", response_model=List[MedicineInventory])
async def replenish_medicines(
    pharmacist: UserAccount = Depends(get_current_pharmacist),
    session: AsyncSession = Depends(get_session),
):
    meds = (await session.execute(select(Medicine))).scalars().all()
    usage_map = await _load_usage_map(session)
    restocked = False
    for med in meds:
        view = _build_inventory_view(med, usage_map)
        if view.suggested_restock > 0:
            med.stock += view.suggested_restock
            session.add(med)
            restocked = True
    if restocked:
        await session.commit()
        meds = (await session.execute(select(Medicine))).scalars().all()
    else:
        await session.rollback()
    return [_build_inventory_view(med, usage_map) for med in meds]


@router.post("/medicines/purchase", response_model=Medicine)
async def purchase_medicine(
    payload: MedicinePurchase,
    pharmacist: UserAccount = Depends(get_current_pharmacist),
    session: AsyncSession = Depends(get_session)
):
    if payload.quantity <= 0:
        raise HTTPException(status_code=400, detail="采购数量必须大于 0")
    med = await session.get(Medicine, payload.medicine_id)
    if not med:
        raise HTTPException(status_code=404, detail="药品不存在")
    med.stock += payload.quantity
    session.add(med)
    await session.commit()
    await session.refresh(med)
    return med


@router.post("/medicines", response_model=Medicine)
async def create_medicine(
    payload: MedicineCreate,
    pharmacist: UserAccount = Depends(get_current_pharmacist),
    session: AsyncSession = Depends(get_session)
):
    # 名称去重校验
    existing = (await session.execute(select(Medicine).where(Medicine.name == payload.name))).scalars().first()
    if existing:
        raise HTTPException(status_code=400, detail="药品名称已存在")
    if payload.price < 0:
        raise HTTPException(status_code=400, detail="单价不能为负数")
    if payload.stock < 0:
        raise HTTPException(status_code=400, detail="库存不能为负数")

    med = Medicine(
        name=payload.name,
        price=payload.price,
        stock=payload.stock,
        unit=payload.unit,
    )
    session.add(med)
    await session.commit()
    await session.refresh(med)
    return med


@router.post("/prescriptions", response_model=PrescriptionRead)
async def create_prescription(
        pres_in: PrescriptionCreate,
        doctor: Doctor = Depends(get_current_doctor),
        session: AsyncSession = Depends(get_session)
):
    # 校验：处方必须关联已有病历，且该病历对应的挂号需已经开始办理（不能在未开始时开处方）
    rec = await session.get(MedicalRecord, pres_in.record_id)
    if not rec:
        raise HTTPException(status_code=404, detail="病历不存在，无法开具处方")

    registration = await session.get(Registration, rec.reg_id)
    if not registration:
        raise HTTPException(status_code=404, detail="关联的挂号单不存在")
    if registration.status == RegStatus.WAITING:
        raise HTTPException(status_code=400, detail="请先开始办理，才能开具处方")
    if registration.doctor_id != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="您不能为非自己接诊的挂号开处方")

    # 检查是否已有处方：如果有则执行“修改处方”的逻辑；否则创建新处方
    existing = (await session.execute(select(Prescription).where(Prescription.record_id == pres_in.record_id))).scalars().first()
    # Helper: load existing details mapping med_id -> qty
    async def _load_existing_details(pres: Prescription):
        stmt = select(PrescriptionDetail).where(PrescriptionDetail.pres_id == pres.pres_id)
        res = await session.execute(stmt)
        rows = res.scalars().all()
        return {r.medicine_id: r.quantity for r in rows}, rows

    total = 0.0

    if existing:
        # 处理库存差异：计算每个 medicine 的 delta = new_qty - old_qty
        old_map, old_rows = await _load_existing_details(existing)
        # build new map
        new_map = {item.medicine_id: item.quantity for item in pres_in.items}

        # first, check stock availability for increases
        for med_id, new_qty in new_map.items():
            old_qty = old_map.get(med_id, 0)
            delta = new_qty - old_qty
            if delta > 0:
                med = await session.get(Medicine, med_id)
                if not med or med.stock < delta:
                    raise HTTPException(status_code=400, detail=f"库存不足: 药品 {med_id}")

        # apply stock adjustments
        for med_id, new_qty in new_map.items():
            old_qty = old_map.get(med_id, 0)
            delta = new_qty - old_qty
            med = await session.get(Medicine, med_id)
            if delta > 0:
                med.stock -= delta
            elif delta < 0:
                med.stock += (-delta)
            session.add(med)

        # 对于旧处方中有但新处方没有的药品，退回库存
        for med_id, old_qty in old_map.items():
            if med_id not in new_map:
                med = await session.get(Medicine, med_id)
                med.stock += old_qty
                session.add(med)

        # 删除旧明细并插入新明细
        for r in old_rows:
            await session.delete(r)

        for item in pres_in.items:
            session.add(PrescriptionDetail(pres_id=existing.pres_id, medicine_id=item.medicine_id, quantity=item.quantity, usage=item.usage))
            med = await session.get(Medicine, item.medicine_id)
            total += med.price * item.quantity

        existing.total_amount = total
        session.add(existing)
        await session.commit()
        await session.refresh(existing)
        return existing

    # 创建新处方
    new_pres = Prescription(record_id=pres_in.record_id, total_amount=0.0)
    session.add(new_pres)
    await session.flush()

    for item in pres_in.items:
        med = await session.get(Medicine, item.medicine_id)
        if not med or med.stock < item.quantity:
            raise HTTPException(status_code=400, detail=f"库存不足: 药品 {item.medicine_id}")
        med.stock -= item.quantity
        session.add(med)
        total += med.price * item.quantity
        session.add(PrescriptionDetail(pres_id=new_pres.pres_id, medicine_id=item.medicine_id, quantity=item.quantity, usage=item.usage))

    new_pres.total_amount = total
    session.add(new_pres)
    await session.commit()
    await session.refresh(new_pres)
    return new_pres


@router.get("/prescriptions/by_record/{record_id}")
async def get_prescription_by_record(
    record_id: int,
    doctor: Doctor = Depends(get_current_doctor),
    session: AsyncSession = Depends(get_session)
):
    # 验证病历与挂号及医生权限
    rec = await session.get(MedicalRecord, record_id)
    if not rec:
        raise HTTPException(status_code=404, detail="病历不存在")
    registration = await session.get(Registration, rec.reg_id)
    if not registration:
        raise HTTPException(status_code=404, detail="关联的挂号单不存在")
    if registration.doctor_id != doctor.doctor_id:
        raise HTTPException(status_code=403, detail="您不能查看非自己接诊的处方")

    pres = (await session.execute(select(Prescription).where(Prescription.record_id == record_id))).scalars().first()
    if not pres:
        raise HTTPException(status_code=404, detail="未找到处方")

    # 拉取明细并返回友好结构
    stmt = select(PrescriptionDetail).where(PrescriptionDetail.pres_id == pres.pres_id)
    details = (await session.execute(stmt)).scalars().all()
    out_details = []
    for d in details:
        med = await session.get(Medicine, d.medicine_id)
        out_details.append({
            "detail_id": d.detail_id,
            "medicine_id": d.medicine_id,
            "medicine_name": med.name if med else None,
            "quantity": d.quantity,
            "usage": d.usage
        })

    return {"pres_id": pres.pres_id, "record_id": pres.record_id, "total_amount": pres.total_amount, "status": pres.status, "details": out_details}