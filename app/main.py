from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlmodel import select
from app.core.config import init_db, get_session, async_session  # 需要导入 async_session
from app.api import auth, patient_service
# 导入所有模型以确保建表
from app.models.user import UserAccount
from app.models.hospital import Department, Doctor, Gender
from app.api import auth, patient_service, doctor_service # <--- 新增 doctor_service
# 记得导入 MedicalRecord 确保建表
from app.models.hospital import MedicalRecord


# --- 辅助：插入测试数据 ---
async def init_data():
    async with async_session() as session:
        # 检查是否有科室，没有则创建
        result = await session.execute(select(Department))
        if not result.scalars().first():
            print("正在插入测试数据：科室和医生...")
            dept1 = Department(dept_name="内科", telephone="1001")
            dept2 = Department(dept_name="外科", telephone="1002")
            session.add(dept1)
            session.add(dept2)
            await session.commit()
            await session.refresh(dept1)

            # 插入医生
            doc1 = Doctor(name="华佗", gender=Gender.MALE, title="主任医师", phone="110", dept_id=dept1.dept_id)
            doc2 = Doctor(name="扁鹊", gender=Gender.MALE, title="副主任医师", phone="120", dept_id=dept1.dept_id)
            session.add(doc1)
            session.add(doc2)
            await session.commit()
            print("测试数据插入完成！")


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("正在初始化数据库表结构...")
    await init_db()
    await init_data()  # <-- 启动时插入数据
    print("系统启动完成！")
    yield


app = FastAPI(title="医院管理系统 API", lifespan=lifespan)

app.include_router(auth.router, prefix="/auth", tags=["认证模块"])
app.include_router(patient_service.router, prefix="/api", tags=["患者服务"])
app.include_router(doctor_service.router, prefix="/api/doctor", tags=["医生工作站"])


@app.get("/")
async def root():
    return {"message": "HMS 后端运行中"}