from sqlmodel import SQLModel
from datetime import datetime

class ScheduleRead(SQLModel):
    schedule_id: int
    nurse_name: str
    ward_type: str
    time: datetime