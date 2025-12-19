import sys
import os

# 把当前目录加入 Python 搜索路径，模拟项目环境
sys.path.append(os.getcwd())

print("--- 开始诊断 ---")
print("1. 尝试导入 app.api.pharmacy_service ...")

try:
    from app.api import pharmacy_service

    print("✅ 导入成功！")
    print(f"2. 检查路由对象: {pharmacy_service.router}")
    print(f"3. 检查路由数量: {len(pharmacy_service.router.routes)}")

    if len(pharmacy_service.router.routes) == 0:
        print("❌ 警告：路由数量为 0！说明 @router.get/.post 装饰器没生效，或者 router = APIRouter() 写错了。")
    else:
        print("✅ 路由看起来很正常。")

except ImportError as e:
    print("\n❌ 致命错误：导入失败！")
    print(f"原因: {e}")
    print("提示：很有可能是 import 写错了，比如从 'patient_service' 导入了已经移除的函数？")
except Exception as e:
    print(f"\n❌ 代码发生了其他错误: {e}")
    import traceback

    traceback.print_exc()

print("--- 诊断结束 ---")