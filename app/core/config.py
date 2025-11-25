from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv
from pathlib import Path

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
    DATABASE_URL = "mysql+aiomysql://root:Henson20070915@localhost:3306/hms_db"
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
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)