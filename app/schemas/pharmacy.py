from sqlmodel import SQLModel
from typing import List
from datetime import datetime

class PresItem(SQLModel):
    medicine_id: int
    quantity: int
    usage: str

class PrescriptionCreate(SQLModel):
    record_id: int
    items: List[PresItem]

# 专门用于返回的 Schema，防止 Swagger 解析报错
class PrescriptionRead(SQLModel):
    pres_id: int
    record_id: int
    total_amount: float
    create_time: datetime


class MedicinePurchase(SQLModel):
    medicine_id: int
    quantity: int


class MedicineCreate(SQLModel):
    name: str
    price: float
    stock: int
    unit: str


class UsagePoint(SQLModel):
    date: str
    quantity: int


class MedicineInventory(SQLModel):
    medicine_id: int
    name: str
    price: float
    stock: int
    unit: str
    usage_30d: int
    avg_daily_usage: float
    expected_week_usage: int
    suggested_restock: int
    needs_restock: bool
    usage_trend: List[UsagePoint]