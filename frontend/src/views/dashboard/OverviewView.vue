<template>
  <div class="overview">
    <template v-if="isNurseRole">
      <div class="title-block">
        <div>
          <h2>病房总览</h2>
          <p class="subtitle">{{ auth.isHeadNurse ? "护士长可查看全部病房" : "仅展示您的值班病房" }}</p>
        </div>
        <el-button v-if="isLoading" type="primary" link :loading="isLoading">加载中</el-button>
      </div>
      <el-empty v-if="!isLoading && wards.length === 0" description="暂无病房数据" />
      <div v-else class="ward-grid">
        <div v-for="ward in wards" :key="ward.ward_id" class="ward-card" @click="handleWardClick(ward)">
          <div class="ward-card__header">
            <div class="ward-badge">病房 {{ ward.ward_id }}</div>
            <span class="ward-type">{{ ward.ward_type }}</span>
          </div>
          <div class="bed-list">
            <div v-for="bed in ward.bed_count" :key="bed" class="bed-slot">床 {{ bed }}</div>
          </div>
        </div>
      </div>

      <el-drawer v-model="recordVisible" :title="activeWardTitle" size="40%" direction="rtl">
        <template #title>
          <div class="drawer-title">
            <span>{{ activeWardTitle }}</span>
            <el-tag size="small" type="info">病历列表</el-tag>
          </div>
        </template>
        <div v-if="recordLoading">
          <el-skeleton :rows="3" animated />
        </div>
        <el-empty v-else-if="wardRecords.length === 0" description="暂无在院病历" />
        <div v-else class="record-list">
          <el-card v-for="item in wardRecords" :key="item.record_id" shadow="hover" class="record-card">
            <div class="record-card__header">
              <div class="record-patient">{{ item.patient_name }}</div>
              <el-tag size="small" type="primary">病历 #{{ item.record_id }}</el-tag>
            </div>
            <div class="record-meta">
              <span>住院号：{{ item.hosp_id }}</span>
              <span>入院时间：{{ formatDate(item.in_date) }}</span>
            </div>
            <div class="record-field"><strong>主诉：</strong>{{ item.complaint }}</div>
            <div class="record-field"><strong>诊断：</strong>{{ item.diagnosis }}</div>
            <div class="record-field" v-if="item.suggestion"><strong>建议：</strong>{{ item.suggestion }}</div>
          </el-card>
        </div>
      </el-drawer>
    </template>

    <template v-else>
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
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { Reading, UserFilled, Suitcase, Histogram } from "@element-plus/icons-vue";
import { useAuthStore } from "../../stores/auth";
import { fetchWardOverview, fetchWardRecords, type WardOverviewItem, type WardRecordItem } from "../../api/modules/nurse";

const auth = useAuthStore();
const isNurseRole = computed(() => auth.currentRole === "护士");
const wards = ref<WardOverviewItem[]>([]);
const isLoading = ref(false);
const recordVisible = ref(false);
const recordLoading = ref(false);
const wardRecords = ref<WardRecordItem[]>([]);
const activeWard = ref<WardOverviewItem | null>(null);

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

async function loadWardOverview() {
  if (!isNurseRole.value) return;
  isLoading.value = true;
  try {
    const { data } = await fetchWardOverview();
    wards.value = data;
  } finally {
    isLoading.value = false;
  }
}

const activeWardTitle = computed(() => {
  if (!activeWard.value) return "病房病历";
  return `病房 ${activeWard.value.ward_id} · ${activeWard.value.ward_type}`;
});

function formatDate(val: string) {
  return new Date(val).toLocaleString();
}

async function handleWardClick(ward: WardOverviewItem) {
  activeWard.value = ward;
  recordVisible.value = true;
  recordLoading.value = true;
  try {
    const { data } = await fetchWardRecords(ward.ward_id);
    wardRecords.value = data;
  } finally {
    recordLoading.value = false;
  }
}

onMounted(() => {
  loadWardOverview();
});
</script>

<style scoped>
.overview {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.title-block {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.subtitle {
  color: #94a3b8;
  margin: 4px 0 0;
}

.ward-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 35px;
  align-items: start;
  justify-items: center;
  grid-auto-rows: 190px;
  max-width: 1050px;
  margin: 0 auto;
}

.ward-card {
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 12px;
  background: linear-gradient(180deg, #f8fafc 0%, #eef2ff 100%);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.06);
  width: 100%;
  max-width: 220px;
  height: 190px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.ward-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 24px rgba(15, 23, 42, 0.08);
}

.ward-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.ward-badge {
  padding: 6px 10px;
  border-radius: 10px;
  background: #312e81;
  color: #fff;
  font-weight: 600;
  letter-spacing: 0.2px;
}

.ward-type {
  color: #475569;
  font-size: 13px;
}

.bed-list {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(80px, 1fr));
  gap: 10px;
  flex: 1;
  overflow-y: auto;
  padding-bottom: 4px;
}

.bed-slot {
  border: 1px solid #cbd5e1;
  border-radius: 10px;
  padding: 10px 12px;
  background: #fff;
  text-align: center;
  font-size: 13px;
  color: #0f172a;
  box-shadow: 0 2px 6px rgba(15, 23, 42, 0.04);
  min-height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.drawer-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.record-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.record-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.record-patient {
  font-weight: 600;
  color: #0f172a;
}

.record-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #475569;
  margin-bottom: 6px;
}

.record-field {
  font-size: 13px;
  color: #0f172a;
  line-height: 1.5;
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
