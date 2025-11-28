<template>
  <div class="overview">
    <el-page-header content="多角色联合工作台" icon="">
      <template #title>
        <span>医院管理系统</span>
      </template>
      <template #content>
        <span>前端遵循《系统设计报告》，并已与当前 MySQL + FastAPI 后端联调</span>
      </template>
    </el-page-header>

    <el-row :gutter="16" class="mt-4">
      <el-col :md="6" :sm="12" v-for="card in featureCards" :key="card.title">
        <el-card shadow="hover" class="feature-card">
          <div class="card-icon" :style="{ background: card.color }">
            <component :is="card.icon" />
          </div>
          <h3>{{ card.title }}</h3>
          <p>{{ card.desc }}</p>
        </el-card>
      </el-col>
    </el-row>

    <el-card class="mt-4">
      <template #header>
        <div class="card-header">
          <span>开发说明</span>
        </div>
      </template>
      <el-timeline>
        <el-timeline-item timestamp="后端" type="success">
          FastAPI + SQLModel + MySQL，提供认证、患者、医生、护士、药房等 REST 接口
        </el-timeline-item>
        <el-timeline-item timestamp="前端" type="primary">
          Vite + Vue 3 + Element Plus，按角色动态授权，所有接口集中于 /auth 与 /api 前缀
        </el-timeline-item>
        <el-timeline-item timestamp="集成" type="warning">
          通过 axios 拦截器携带 Token，Vite Proxy 映射到 uvicorn 8001 端口
        </el-timeline-item>
        <el-timeline-item timestamp="后续扩展" type="info">
          可在 vue-router 中新增视图以覆盖护士长、统计分析、营收 BI 等设计报告中的扩展模块
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { Reading, UserFilled, Suitcase, Histogram } from "@element-plus/icons-vue";

const featureCards = [
  {
    title: "患者门户",
    desc: "完善档案、查看科室、医生并提交挂号申请",
    icon: UserFilled,
    color: "#fce7f3"
  },
  {
    title: "医生工作站",
    desc: "处理待诊挂号、填写病历并联动处方流",
    icon: Suitcase,
    color: "#e0f2fe"
  },
  {
    title: "护士/药房",
    desc: "排班总览、药品库存与处方编制",
    icon: Reading,
    color: "#e2e8f0"
  },
  {
    title: "管理驾驶舱",
    desc: "为管理员保留扩展入口，可挂接统计与营收分析",
    icon: Histogram,
    color: "#fef3c7"
  }
];
</script>

<style scoped>
.overview {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.mt-4 {
  margin-top: 16px;
}

.feature-card {
  min-height: 150px;
}

.card-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.card-icon :deep(svg) {
  width: 24px;
  height: 24px;
}
</style>
