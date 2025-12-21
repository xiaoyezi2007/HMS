from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select

from app.models.hospital import Hospitalization, Medicine, NurseTask

DEFAULT_HOSPITAL_HOURLY_RATE = 80.0


def _safe_load_snapshot(snapshot: Optional[str]) -> List[Dict[str, Any]]:
    if not snapshot:
        return []
    try:
        data = json.loads(snapshot)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    return []


async def compute_hospitalization_bill(
    session: AsyncSession,
    hospitalization: Hospitalization,
    hourly_rate: float = DEFAULT_HOSPITAL_HOURLY_RATE,
    reference_end: Optional[datetime] = None,
) -> Dict[str, Any]:
    if not hospitalization.in_date:
        return {
            "base_hours": 0.0,
            "base_fee": 0.0,
            "medicine_fee": 0.0,
            "service_fee": 0.0,
            "total_fee": 0.0,
            "tasks": [],
        }

    end_time = reference_end or hospitalization.out_date or datetime.now()
    base_hours = max((end_time - hospitalization.in_date).total_seconds() / 3600, 0.5)
    base_fee = round(base_hours * hourly_rate, 2)

    task_stmt = (
        select(NurseTask)
        .where(NurseTask.hosp_id == hospitalization.hosp_id)
        .order_by(NurseTask.time.asc(), NurseTask.task_id.asc())
    )
    tasks = (await session.execute(task_stmt)).scalars().all()

    price_cache: Dict[int, float] = {}
    task_details: List[Dict[str, Any]] = []
    total_medicine_fee = 0.0
    total_service_fee = 0.0

    for task in tasks:
        medicine_items: List[Dict[str, Any]] = []
        medicine_fee = 0.0
        for item in _safe_load_snapshot(task.medicine_snapshot):
            med_id = item.get("medicine_id")
            quantity = item.get("quantity")
            if not med_id or not quantity:
                continue
            if med_id not in price_cache:
                medicine = await session.get(Medicine, med_id)
                price_cache[med_id] = float(medicine.price) if medicine else 0.0
            unit_price = price_cache[med_id]
            subtotal = round(unit_price * quantity, 2)
            medicine_fee += subtotal
            medicine_items.append({
                "medicine_id": med_id,
                "name": item.get("name"),
                "usage": item.get("usage"),
                "quantity": quantity,
                "unit_price": unit_price,
                "subtotal": subtotal,
            })

        service_fee = round(task.service_fee or 0.0, 2)
        total_medicine_fee += medicine_fee
        total_service_fee += service_fee

        task_details.append({
            "task_id": task.task_id,
            "type": task.type,
            "time": task.time,
            "status": task.status,
            "detail": task.detail,
            "medicine_fee": round(medicine_fee, 2),
            "service_fee": service_fee,
            "total_fee": round(medicine_fee + service_fee, 2),
            "medicines": medicine_items,
        })

    total_amount = round(base_fee + total_medicine_fee + total_service_fee, 2)

    return {
        "base_hours": round(base_hours, 2),
        "base_fee": base_fee,
        "medicine_fee": round(total_medicine_fee, 2),
        "service_fee": round(total_service_fee, 2),
        "total_fee": total_amount,
        "tasks": task_details,
    }
