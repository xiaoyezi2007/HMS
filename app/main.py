from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlmodel import select
from app.core.config import init_db, async_session

# 导入所有模块
from app.api import auth, patient_service, doctor_service, nurse_service, pharmacy_service

# 导入模型
from app.models.user import UserAccount
from app.models.hospital import Department, Doctor, Gender, Medicine, Nurse, Ward, NurseSchedule
from datetime import date, datetime


async def init_data():
    async with async_session() as session:
        # 1. 科室与医生
        if not (await session.execute(select(Department))).scalars().first():
            d1 = Department(dept_name="内科", telephone="1001")
            session.add(d1)
            await session.commit()
            await session.refresh(d1)
            session.add(Doctor(name="华佗", gender=Gender.MALE, title="主任", phone="110", dept_id=d1.dept_id))
            await session.commit()

        # 2. 药品
        if not (await session.execute(select(Medicine))).scalars().first():
            session.add(Medicine(name="布洛芬", price=30.0, stock=100, unit="盒", expire_date=date(2025, 12, 1)))
            await session.commit()

        # 3. 护士与病房
        if not (await session.execute(select(Nurse))).scalars().first():
            d1 = (await session.execute(select(Department))).scalars().first()
            if d1:
                w1 = Ward(bed_count=4, type="普通房", dept_id=d1.dept_id)
                session.add(w1)
                await session.flush()
                n1 = Nurse(name="南丁格尔", gender=Gender.FEMALE, phone="123")
                session.add(n1)
                await session.flush()
                session.add(NurseSchedule(nurse_id=n1.nurse_id, ward_id=w1.ward_id, time=datetime.now()))
                await session.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("初始化表结构...")
    await init_db()
    await init_data()
    print("启动完成！")
    yield


app = FastAPI(title="医院管理系统 API", lifespan=lifespan)

app.include_router(auth.router, prefix="/auth", tags=["认证模块"])
app.include_router(patient_service.router, prefix="/api", tags=["患者服务"])
app.include_router(doctor_service.router, prefix="/api/doctor", tags=["医生工作站"])
app.include_router(nurse_service.router, prefix="/api/nurse", tags=["护士工作站"])
app.include_router(pharmacy_service.router, prefix="/api/pharmacy", tags=["药房管理"])


@app.get("/")
async def root():
    return {"message": "HMS Running on Port 8001"}