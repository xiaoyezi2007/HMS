# HMS 前端（Vue 3 + Vite）

本项目实现了《系统设计报告》中“患者门户 / 医生工作站 / 护士工作站 / 药房管理 / 管理驾驶舱”等核心模块的 Web 前端，已与当前 **FastAPI + SQLModel + MySQL** 后端接口对接。

## 功能映射

| 设计角色 | 前端页面 | 对应接口 |
| --- | --- | --- |
| 患者 | 患者门户：档案维护、科室/医生查询、挂号 | `/api/profile`, `/api/departments`, `/api/doctors/{id}`, `/api/registrations` |
| 医生 | 医生工作站：待诊列表、病历书写 | `/api/doctor/schedule`, `/api/doctor/consultations/{reg_id}` |
| 护士 | 护士看板：排班总览 | `/api/nurse/my_schedules` |
| 药师 / 医生 | 处方中心：库存查询、处方提交 | `/api/pharmacy/medicines`, `/api/pharmacy/prescriptions` |
| 管理员 | 驾驶舱：保留扩展入口，便于挂接统计/营收模块 | 预留路由，后端扩展后可继续接入 |

> 说明：后端目前基于 MySQL（非设计文档中的 SQL Server），但前端接口与数据库实现解耦，无需额外处理。

## 技术栈

- Vite 5 + Vue 3 + TypeScript
- Pinia 管理登录态（Token + 角色）
- Vue Router 动态路由守卫（按 `role` 精确授权）
- Element Plus 组件库 + axios + dayjs
- Vite 代理 `/auth` & `/api` 到 `http://127.0.0.1:8001`

## 快速开始

```bash
cd frontend
npm install
npm run dev        # 默认 5173 端口，已通过代理联调 uvicorn 8001
npm run build
```

## 目录结构

```
frontend/
├── src/
│   ├── api/          # axios 封装与接口模块
│   ├── components/   # 布局组件
│   ├── router/       # 路由与权限控制
│   ├── stores/       # Pinia 状态
│   └── views/        # 各角色页面
└── vite.config.ts    # 启动代理、本地端口配置
```

## 后续扩展建议

1. 在 `views/dashboard` 中新增护士长、统计分析等页面；
2. 若后端补充管理员接口，可在 `AdminDashboard` 内对接数据可视化（ECharts 等）；
3. 挂号列表、缴费记录等可在 `patient` 视图中扩展新的 API 列表卡片。
