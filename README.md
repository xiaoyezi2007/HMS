# 使用手册

## 1. 数据库启动与配置

1. 启动本地 MySQL 服务，例如在 Windows：
	```powershell
	mysql -u root -p
	```
2. 创建数据库：
	```sql
	CREATE DATABASE IF NOT EXISTS hms_db;
	```
3. 在项目根目录编辑 `.env`，设置 `DATABASE_URL`：

	```env
	DATABASE_URL=mysql+aiomysql://root:你的密码@127.0.0.1:3306/hms_db
	```

    若失败则在app/core/config.py直接修改。

## 3. 后端运行指令

```powershell
pip install -r requirements.txt        # 首次需要
uvicorn app.main:app --reload          # 默认绑定 http://127.0.0.1:8001
```

- `init_db()` 会在启动时自动建表 + 注入默认院长账户（手机号 `19999999999`，密码 `Director@123`）。

## 4. 前端运行指令

```powershell
cd HMS\frontend
npm install          # 首次需要
npm run dev          # 默认 http://127.0.0.1:5173
```