from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from sqlmodel import select
from sqlalchemy import text
from app.core.config import init_db, async_session
from app.core.security import get_password_hash, SECRET_KEY, ALGORITHM
from jose import jwt, JWTError
from app.core.time_utils import now_bj

# 导入所有模块
from app.api import auth, patient_service, doctor_service, nurse_service, pharmacy_service, admin_service

# 导入模型
from app.models.user import UserAccount, UserRole, UserActionLog
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



async def init_triggers():
    """Remove legacy trigger that injected random exam fees."""
    async with async_session() as session:
        conn = await session.connection()
        try:
            await conn.execute(text("DROP TRIGGER IF EXISTS trg_registration_completed"))
        except Exception as exc:  # noqa: W0703
            print(f"WARN: failed to drop trigger trg_registration_completed: {exc}")



@asynccontextmanager
async def lifespan(app: FastAPI):
    print("初始化表结构...")
    await init_db()
    await init_data()
    await init_triggers()
    print("启动完成！")
    yield


app = FastAPI(title="医院管理系统 API", lifespan=lifespan)


@app.middleware("http")
async def audit_log_middleware(request: Request, call_next):
    response = await call_next(request)

    path = request.url.path
    skip_prefixes = ("/docs", "/openapi.json", "/redoc", "/static")
    if path == "/" or any(path.startswith(prefix) for prefix in skip_prefixes):
        return response

    auth_header = request.headers.get("Authorization", "")
    user_phone = None
    role = None
    if auth_header.lower().startswith("bearer "):
        token = auth_header.split(" ", 1)[1]
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            user_phone = payload.get("sub")
            role = payload.get("role")
        except JWTError:
            pass

    if user_phone:
        try:
            async with async_session() as session:
                log = UserActionLog(
                    user_phone=user_phone,
                    role=str(role or ""),
                    method=request.method,
                    path=path,
                    action=f"{request.method} {path}",
                    status_code=response.status_code,
                    ip_address=request.client.host if request.client else "unknown",
                    created_at=now_bj(),
                )
                session.add(log)
                await session.commit()
        except Exception as exc:  # noqa: W0703
            print(f"WARN: failed to record user action log: {exc}")

    return response

app.include_router(auth.router, prefix="/auth", tags=["认证模块"])
app.include_router(patient_service.router, prefix="/api", tags=["患者服务"])
app.include_router(doctor_service.router, prefix="/api/doctor", tags=["医生工作站"])
app.include_router(nurse_service.router, prefix="/api/nurse", tags=["护士工作站"])
app.include_router(pharmacy_service.router, prefix="/api/pharmacy", tags=["药房管理"])
app.include_router(admin_service.router, prefix="/api", tags=["管理员"])


@app.get("/")
async def root():
    return {"message": "HMS Running on Port 8001"}