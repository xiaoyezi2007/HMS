<template>
  <div class="revenue-board">
    <el-card shadow="hover" class="summary-card">
      <template #header>
        <div class="card-header">
          <div>
            <span>院长营收驾驶舱</span>
            <small>实时掌握医院收入脉搏</small>
          </div>
          <div class="header-actions">
            <el-button type="success" plain :disabled="!hasTypeData" @click="exportChartImage">导出图表</el-button>
            <el-button type="primary" :loading="loading" @click="loadSummary">刷新数据</el-button>
          </div>
        </div>
      </template>
      <el-row :gutter="16" class="summary-grid">
        <el-col :xs="24" :md="12">
          <div class="metric highlight">
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
      <div class="divider-spacer">
        <el-divider class="summary-divider" />
      </div>
      <div class="chart-section">
        <div class="chart-head">
          <div>
            <div class="chart-title">收入类型占比</div>
            <small>用一张图概览处方、检查、住院等收入贡献</small>
          </div>
        </div>
        <div class="chart-wrapper" ref="chartRef" v-show="hasTypeData"></div>
        <el-empty v-if="!hasTypeData" description="暂无营收数据" />
      </div>
      <div class="type-breakdown" v-if="hasTypeData">
        <div class="type-item" v-for="item in summary?.by_type" :key="item.type">
          <div class="type-label">{{ item.type }}</div>
          <div class="type-amount">¥{{ formatAmount(item.amount) }}</div>
          <div class="type-count">{{ item.count }} 笔</div>
        </div>
      </div>
    </el-card>

    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <div>
            <span>营收明细</span>
            <small>展示最近 200 条已缴费记录</small>
          </div>
          <div class="header-actions">
            <el-button type="success" plain :disabled="!hasRecords" @click="exportTableCsv">导出表格</el-button>
          </div>
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
import { computed, nextTick, onMounted, onUnmounted, ref } from "vue";
import { ElMessage } from "element-plus";
import * as echarts from "echarts";
import dayjs from "dayjs";
import { fetchRevenueSummary, type RevenueSummary } from "../../api/modules/admin";

const summary = ref<RevenueSummary | null>(null);
const loading = ref(false);
const chartRef = ref<HTMLDivElement | null>(null);
const hasTypeData = computed(() => Boolean(summary.value?.by_type?.length));
const hasRecords = computed(() => Boolean(summary.value?.records?.length));
let chartInstance: echarts.ECharts | null = null;

async function loadSummary() {
  loading.value = true;
  try {
    const { data } = await fetchRevenueSummary();
    summary.value = data;
    await nextTick();
    renderChart();
  } catch (err: any) {
    const message = err?.response?.data?.detail ?? "营收数据加载失败";
    ElMessage.error(message);
  } finally {
    loading.value = false;
  }
}

function renderChart() {
  if (!chartRef.value || !hasTypeData.value) {
    disposeChart();
    return;
  }

  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value);
  }

  const chartData = summary.value?.by_type?.map((item) => ({
    name: item.type,
    value: item.amount,
    count: item.count
  })) || [];

  chartInstance.setOption({
    tooltip: {
      trigger: "item",
      formatter: (params: any) => {
        const value = params.data?.value ?? 0;
        const count = params.data?.count ?? 0;
        return `${params.name}<br/>金额：¥${formatAmount(value)}<br/>笔数：${count}`;
      }
    },
    legend: {
      bottom: 0,
      icon: "circle"
    },
    series: [
      {
        name: "收入类型",
        type: "pie",
        radius: ["40%", "70%"],
        center: ["50%", "50%"],
        avoidLabelOverlap: false,
        itemStyle: {
          borderRadius: 4,
          borderColor: "#f8fafc",
          borderWidth: 2
        },
        label: {
          formatter: "{b}\n{d}%",
          fontSize: 12
        },
        emphasis: {
          label: {
            show: true,
            fontWeight: "bold"
          }
        },
        data: chartData
      }
    ]
  });
}

function disposeChart() {
  if (chartInstance) {
    chartInstance.dispose();
    chartInstance = null;
  }
}

function handleResize() {
  chartInstance?.resize();
}

function exportChartImage() {
  if (!chartInstance || !hasTypeData.value) {
    ElMessage.warning("暂无可导出的图表");
    return;
  }
  const url = chartInstance.getDataURL({ type: "png", pixelRatio: 2, backgroundColor: "#ffffff" });
  const link = document.createElement("a");
  link.href = url;
  link.download = `revenue-chart-${dayjs().format("YYYYMMDD-HHmmss")}.png`;
  link.click();
}

function exportTableCsv() {
  if (!hasRecords.value || !summary.value?.records) {
    ElMessage.warning("暂无可导出的明细");
    return;
  }

  const headers = ["单号", "类型", "金额", "患者姓名", "患者电话", "缴费时间"];
  const rows = summary.value.records.map((item) => [
    item.payment_id,
    item.type,
    formatAmount(item.amount),
    item.patient_name || "",
    item.patient_phone || "",
    formatDate(item.time)
  ]);

  const csvContent = [headers, ...rows]
    .map((row) => row.map((cell) => `"${String(cell ?? "").replace(/"/g, '""')}"`).join(","))
    .join("\n");

  const blob = new Blob(["\ufeff" + csvContent], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `revenue-records-${dayjs().format("YYYYMMDD-HHmmss")}.csv`;
  link.click();
  URL.revokeObjectURL(url);
  ElMessage.success("表格已导出");
}

function formatAmount(value?: number) {
  return (value ?? 0).toFixed(2);
}

function formatDate(value?: string) {
  if (!value) {
    return "-";
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}

onMounted(() => {
  window.addEventListener("resize", handleResize);
  void loadSummary();
});

onUnmounted(() => {
  window.removeEventListener("resize", handleResize);
  disposeChart();
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
  gap: 12px;
}

.card-header small {
  color: #94a3b8;
  display: block;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.summary-grid {
  margin-bottom: 8px;
}

.summary-divider {
  margin: 16px 0 18px;
}

.divider-spacer {
  padding-top: 8px;
  padding-bottom: 8px;
}

.metric {
  background: #f8fafc;
  border-radius: 12px;
  padding: 16px;
  height: 100%;
}

.metric.highlight {
  background: linear-gradient(135deg, #0ea5e9, #2563eb);
  color: #fff;
}

.metric.highlight .metric-label {
  color: rgba(255, 255, 255, 0.8);
}

.metric-label {
  color: #64748b;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 28px;
  font-weight: 600;
}

.chart-section {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 14px;
  padding-top: 6px;
}

.chart-head .chart-title {
  font-size: 16px;
  font-weight: 600;
}

.chart-wrapper {
  width: 100%;
  height: 320px;
  margin-top: 10px;
}

.type-breakdown {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  margin-top: 16px;
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

@media (max-width: 768px) {
  .card-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .metric-value {
    font-size: 22px;
  }
}
</style>
