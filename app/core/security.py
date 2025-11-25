import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from jose import jwt

# 密钥配置
SECRET_KEY = "hms-secret-key-change-me-in-production"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30


# --- 密码相关函数 (直接使用 bcrypt 库) ---
def verify_password(plain_password, hashed_password):
    """验证密码是否正确"""
    # bcrypt 需要字节串(bytes)，所以要 encode
    # 数据库里的 hash 如果是 str，也要 encode 成 bytes
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')

    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password)


def get_password_hash(password):
    """将明文密码加密"""
    # 生成 salt 并加密
    pwd_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')  # 存入数据库时转回字符串


# --- Token 相关函数 (保持不变) ---
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt