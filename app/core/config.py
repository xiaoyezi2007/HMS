from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy import text
import asyncio
import re

# 1. 定位项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"

# --- 调试打印开始 ---
print(f"DEBUG: 项目根目录是: {BASE_DIR}")
print(f"DEBUG: 尝试加载 .env 文件路径: {env_path}")
print(f"DEBUG: 该文件真的存在吗? {env_path.exists()}")
# --- 调试打印结束 ---

load_dotenv(dotenv_path=env_path)

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    # 如果还是读不到，咱们直接在这里打印出来看看 env 文件内容有没有被读成其他的
    print("DEBUG: 环境变量读取失败。")
    # --- 终极临时方案：如果为了先跑通，可以暂时取消下面这行的注释，把 URL 硬编码在这里 ---
    DATABASE_URL = "mysql+aiomysql://root:Y9y4iyJZ3FsQGAJ4USN3Pmbvd0VgwKA@localhost:3306/hms_db"
else:
    print(f"DEBUG: 成功获取数据库地址: {DATABASE_URL}")

# 再次检查
if not DATABASE_URL:
     raise ValueError("严重错误：未找到 DATABASE_URL 环境变量！请检查 .env 文件名为 .env 且没有 .txt 后缀")

engine = create_async_engine(DATABASE_URL, echo=True, future=True)

async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

async def init_db():
    # 为避免在使用 uvicorn --reload 或多进程/多线程启动时多个进程同时执行 DDL
    # 导致 "table ... was skipped since its definition is being modified by concurrent DDL" 错误，
    # 在 MySQL 上使用命名锁（GET_LOCK）保护 create_all 的执行。
    async with engine.begin() as conn:
        try:
            # 如果是 MySQL，尝试获取命名锁；否则直接创建
            if DATABASE_URL and ("mysql" in DATABASE_URL or "mariadb" in DATABASE_URL):
                # 等待最多 10 秒获取锁，获取成功返回 1
                got = await conn.execute(text("SELECT GET_LOCK('hms_init_db_lock', 10)"))
                val = got.scalar()
                if val != 1:
                    # 未能获取锁，等待并重试一次
                    await asyncio.sleep(1)
                    got = await conn.execute(text("SELECT GET_LOCK('hms_init_db_lock', 10)"))
                    val = got.scalar()
                if val == 1:
                    await conn.run_sync(SQLModel.metadata.create_all)

                    # ---- lightweight migrations (MySQL) ----
                    # Add visit_date column to registration table if missing.
                    try:
                        exists = await conn.execute(
                            text(
                                """
                                SELECT COUNT(*)
                                FROM information_schema.columns
                                WHERE table_schema = DATABASE()
                                  AND table_name = 'registration'
                                  AND column_name = 'visit_date'
                                """
                            )
                        )
                        if (exists.scalar() or 0) == 0:
                            await conn.execute(text("ALTER TABLE registration ADD COLUMN visit_date DATE NOT NULL DEFAULT (CURRENT_DATE)"))
                    except Exception:
                        # best-effort: don't block app startup if migration fails
                        pass

                    # Extend registration.status ENUM to include EXPIRED if needed.
                    try:
                        col = await conn.execute(
                            text(
                                """
                                SELECT COLUMN_TYPE
                                FROM information_schema.columns
                                WHERE table_schema = DATABASE()
                                  AND table_name = 'registration'
                                  AND column_name = 'status'
                                """
                            )
                        )
                        column_type = col.scalar() or ""
                        if isinstance(column_type, str) and column_type.lower().startswith("enum("):
                            values = re.findall(r"'([^']*)'", column_type)
                            # Decide whether DB stores enum names (WAITING/...) or Chinese values.
                            wants_name = any(v in ("WAITING", "IN_PROGRESS", "FINISHED", "CANCELLED") for v in values)
                            expired_token = "EXPIRED" if wants_name else "已过期"
                            if expired_token not in values:
                                new_values = values + [expired_token]
                                # Preserve default when possible
                                default_token = "WAITING" if "WAITING" in values else ("排队中" if "排队中" in values else (values[0] if values else expired_token))
                                enum_sql = ",".join([f"'{v}'" for v in new_values])
                                await conn.execute(
                                    text(
                                        f"ALTER TABLE registration MODIFY COLUMN status ENUM({enum_sql}) NOT NULL DEFAULT '{default_token}'"
                                    )
                                )
                    except Exception:
                        pass

                    # Add reg_id column to payment table if missing.
                    try:
                        exists = await conn.execute(
                            text(
                                """
                                SELECT COUNT(*)
                                FROM information_schema.columns
                                WHERE table_schema = DATABASE()
                                  AND table_name = 'payment'
                                  AND column_name = 'reg_id'
                                """
                            )
                        )
                        if (exists.scalar() or 0) == 0:
                            await conn.execute(text("ALTER TABLE payment ADD COLUMN reg_id INTEGER NULL"))
                    except Exception:
                        pass

                    # 释放锁
                    await conn.execute(text("SELECT RELEASE_LOCK('hms_init_db_lock')"))
                else:
                    # 如果仍未获取锁，直接尝试创建（可能会抛出异常，外层会记录）
                    await conn.run_sync(SQLModel.metadata.create_all)
            else:
                await conn.run_sync(SQLModel.metadata.create_all)
        finally:
            # 最后兜底：确保锁被释放（若连接上未持有锁则 RELEASE_LOCK 返回 NULL）
            try:
                await conn.execute(text("SELECT RELEASE_LOCK('hms_init_db_lock')"))
            except Exception:
                pass