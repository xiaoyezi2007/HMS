from fastapi import FastAPI
from contextlib import asynccontextmanager
from sqlmodel import select
from sqlalchemy import text
from app.core.config import init_db, async_session
from app.core.security import get_password_hash

# 导入所有模块
from app.api import auth, patient_service, doctor_service, nurse_service, pharmacy_service, admin_service

# 导入模型
from app.models.user import UserAccount, UserRole
from app.models.hospital import Department, Doctor, Gender, Medicine, Nurse, Ward, NurseSchedule
from datetime import datetime


async def init_data():
    async with async_session() as session:
        # 0. 默认院长账号（唯一管理员/院长）
        director_phone = "19999999999"
        director_username = "院长"
        director_password = "Director@123"

        existing_director = (await session.execute(select(UserAccount).where(UserAccount.phone == director_phone))).scalars().first()
        if not existing_director:
            director_account = UserAccount(
                phone=director_phone,
                username=director_username,
                role=UserRole.ADMIN,
                password_hash=get_password_hash(director_password),
                status="启用"
            )
            session.add(director_account)
            await session.commit()

        # 1. 科室（示例数据）
        if not (await session.execute(select(Department))).scalars().first():
            departments = [
                Department(dept_name="内科", telephone="1001"),
                Department(dept_name="外科", telephone="1002"),
                Department(dept_name="儿科", telephone="1003"),
                Department(dept_name="妇产科", telephone="1004"),
                Department(dept_name="骨科", telephone="1005"),
                Department(dept_name="眼科", telephone="1006"),
                Department(dept_name="耳鼻喉科", telephone="1007"),
                Department(dept_name="口腔科", telephone="1008"),
                Department(dept_name="皮肤科", telephone="1009"),
                Department(dept_name="中医科", telephone="1010")
            ]
            session.add_all(departments)
            await session.commit()
            d1 = (await session.execute(select(Department))).scalars().first()

        # 2. 药品
        if not (await session.execute(select(Medicine))).scalars().first():
            session.add(Medicine(name="布洛芬", price=30.0, stock=100, unit="盒"))
            await session.commit()

        # 3. 护士与病房
        if not (await session.execute(select(Nurse))).scalars().first():
            d1 = (await session.execute(select(Department))).scalars().first()
            if d1:
                w1 = Ward(bed_count=4, type="普通房", dept_id=d1.dept_id)
                session.add(w1)
                await session.flush()


async def init_triggers():
    """Create or replace database triggers needed by the app."""
    trigger_sql = """
    CREATE TRIGGER trg_registration_completed
    AFTER UPDATE ON registration
    FOR EACH ROW
    BEGIN
        IF OLD.status <> 'FINISHED' AND NEW.status = 'FINISHED' THEN
            INSERT INTO payment(type, amount, patient_id, reg_id, pres_id, time)
            SELECT 'PRESCRIPTION', pres.total_amount, NEW.patient_id, NEW.reg_id, pres.pres_id, NOW()
            FROM prescription pres
            JOIN medicalrecord mr ON mr.record_id = pres.record_id
            WHERE mr.reg_id = NEW.reg_id;

            INSERT INTO payment(type, amount, patient_id, reg_id, exam_id, time)
            SELECT 'EXAM', FLOOR(RAND() * 151) + 50, NEW.patient_id, NEW.reg_id, exam.exam_id, NOW()
            FROM examination exam
            JOIN medicalrecord mr ON mr.record_id = exam.record_id
            WHERE mr.reg_id = NEW.reg_id;
        END IF;
    END;
    """

    async with async_session() as session:
        conn = await session.connection()
        # Drop then create to ensure latest definition is in place
        try:
            await conn.execute(text("DROP TRIGGER IF EXISTS trg_registration_completed"))
        except Exception:
            pass
        try:
            await conn.execute(text(trigger_sql))
        except Exception as exc:
            # Keep startup running even if trigger creation fails
            print(f"WARN: failed to create trigger trg_registration_completed: {exc}")



@asynccontextmanager
async def lifespan(app: FastAPI):
    print("初始化表结构...")
    await init_db()
    await init_data()
    await init_triggers()
    print("启动完成！")
    yield


app = FastAPI(title="医院管理系统 API", lifespan=lifespan)

app.include_router(auth.router, prefix="/auth", tags=["认证模块"])
app.include_router(patient_service.router, prefix="/api", tags=["患者服务"])
app.include_router(doctor_service.router, prefix="/api/doctor", tags=["医生工作站"])
app.include_router(nurse_service.router, prefix="/api/nurse", tags=["护士工作站"])
app.include_router(pharmacy_service.router, prefix="/api/pharmacy", tags=["药房管理"])
app.include_router(admin_service.router, prefix="/api", tags=["管理员"])


@app.get("/")
async def root():
    return {"message": "HMS Running on Port 8001"}