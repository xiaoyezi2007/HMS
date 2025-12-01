<template>
  <div class="revenue-board">
    <el-card shadow="hover" class="summary-card">
      <template #header>
        <div class="card-header">
          <span>营收总览</span>
          <small>统计所有已缴费项目，实时掌握医院营收</small>
        </div>
        <el-button type="primary" link :loading="loading" @click="loadSummary">刷新</el-button>
      </template>
      <el-row :gutter="16">
        <el-col :xs="24" :md="12">
          <div class="metric">
            <div class="metric-label">累计营收</div>
            <div class="metric-value">¥{{ formatAmount(summary?.total_amount) }}</div>
          </div>
        </el-col>
        <el-col :xs="24" :md="12">
          <div class="metric">
            <div class="metric-label">已缴费笔数</div>
            <div class="metric-value">{{ summary?.paid_count ?? 0 }} 笔</div>
          </div>
        </el-col>
      </el-row>
      <el-divider />
      <div class="type-breakdown" v-if="summary?.by_type?.length">
        <div class="type-item" v-for="item in summary.by_type" :key="item.type">
          <div class="type-label">{{ item.type }}</div>
          <div class="type-amount">¥{{ formatAmount(item.amount) }}</div>
          <div class="type-count">{{ item.count }} 笔</div>
        </div>
      </div>
      <el-empty v-else description="暂无营收数据" />
    </el-card>

    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>营收明细</span>
          <small>展示最近 200 条已缴费记录</small>
        </div>
      </template>
      <el-table :data="summary?.records || []" v-loading="loading" empty-text="暂无缴费记录">
        <el-table-column prop="payment_id" label="单号" width="120" />
        <el-table-column prop="type" label="类型" width="120" />
        <el-table-column label="金额" width="120">
          <template #default="{ row }">
            ¥{{ formatAmount(row.amount) }}
          </template>
        </el-table-column>
        <el-table-column label="患者" min-width="180">
          <template #default="{ row }">
            <div>{{ row.patient_name || '未知患者' }}</div>
            <small class="text-muted">{{ row.patient_phone || '-' }}</small>
          </template>
        </el-table-column>
        <el-table-column prop="time" label="缴费时间" min-width="200">
          <template #default="{ row }">
            {{ formatDate(row.time) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { fetchRevenueSummary, type RevenueSummary } from "../../api/modules/admin";

const summary = ref<RevenueSummary | null>(null);
const loading = ref(false);

async function loadSummary() {
  loading.value = true;
  try {
    const { data } = await fetchRevenueSummary();
    summary.value = data;
  } catch (err: any) {
    const message = err?.response?.data?.detail ?? "营收数据加载失败";
    ElMessage.error(message);
  } finally {
    loading.value = false;
  }
}

function formatAmount(value?: number) {
  return (value ?? 0).toFixed(2);
}

function formatDate(value?: string) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  return isNaN(date.getTime()) ? value : date.toLocaleString();
}

onMounted(() => {
  void loadSummary();
});
</script>

<style scoped>
.revenue-board {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header small {
  color: #94a3b8;
}

.metric {
  background: #f8fafc;
  border-radius: 8px;
  padding: 16px;
}

.metric-label {
  color: #64748b;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 28px;
  font-weight: 600;
}

.type-breakdown {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.type-item {
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 12px 16px;
  min-width: 180px;
}

.type-label {
  font-weight: 600;
  margin-bottom: 4px;
}

.type-amount {
  color: #111827;
}

.type-count {
  color: #94a3b8;
}

.text-muted {
  color: #94a3b8;
}
</style>
