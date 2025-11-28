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
    status: str
    create_time: datetime


class MedicinePurchase(SQLModel):
    medicine_id: int
    quantity: int