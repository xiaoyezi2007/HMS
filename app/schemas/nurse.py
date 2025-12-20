from datetime import datetime
from typing import List, Optional

from sqlmodel import Field, SQLModel


class ScheduleRead(SQLModel):
    schedule_id: int
    nurse_name: str
    ward_type: str
    start_time: datetime
    end_time: datetime


class NurseProfile(SQLModel):
    nurse_id: int
    name: str
    is_head_nurse: bool


class NurseOption(SQLModel):
    nurse_id: int
    name: str
    is_head_nurse: bool


class WardScheduleEntry(SQLModel):
    schedule_id: int
    nurse_id: int
    nurse_name: str
    start_time: datetime
    end_time: datetime


class WardScheduleGroup(SQLModel):
    ward_id: int
    ward_type: str
    schedules: List[WardScheduleEntry]


class WardOverviewItem(SQLModel):
    ward_id: int
    ward_type: str
    bed_count: int


class WardRecordItem(SQLModel):
    ward_id: int
    ward_type: str
    hosp_id: int
    record_id: int
    patient_id: int
    patient_name: str
    complaint: str
    diagnosis: str
    suggestion: Optional[str] = None
    in_date: datetime


class HeadScheduleContext(SQLModel):
    wards: List[WardScheduleGroup]
    nurses: List[NurseOption]


class ScheduleUpsertPayload(SQLModel):
    ward_id: int
    start_time: datetime
    end_time: datetime
    nurse_ids: List[int] = Field(default_factory=list)
    source_ward_id: Optional[int] = None
    source_start_time: Optional[datetime] = None
    source_end_time: Optional[datetime] = None


class AutoScheduleRequest(SQLModel):
    start_time: Optional[datetime] = None
    shift_hours: int = Field(default=8, gt=0, le=24)
    shift_count: int = Field(default=3, gt=0, le=24)
    ward_ids: Optional[List[int]] = None