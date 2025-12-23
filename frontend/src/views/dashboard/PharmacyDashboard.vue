<template>
  <div class="pharmacy-board">
    <el-card class="warning-card">
      <template #header>
        <div class="card-header">
          <span>库存预警</span>
          <small>库存低于 {{ lowStockThreshold }} 或无法覆盖未来 {{ planningHorizonDays }} 天需求的药品会在此处提示</small>
        </div>
      </template>
      <div v-if="lowStockList.length">
        <el-alert
          title="以下药品库存紧张，建议按照用量建议尽快补足"
          type="warning"
          show-icon
          :closable="false"
        >
          <template #description>
            <el-table :data="lowStockList" size="mini" stripe>
              <el-table-column prop="name" label="药品" min-width="140" />
              <el-table-column prop="unit" label="单位" width="80" />
              <el-table-column prop="stock" label="库存" width="90">
                <template #default="{ row }">
                  <el-tag type="danger">{{ row.stock }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="近30天用量" width="120">
                <template #default="{ row }">
                  {{ row.usage_30d || 0 }}
                </template>
              </el-table-column>
              <el-table-column label="预计7天用量" width="120">
                <template #default="{ row }">
                  {{ row.expected_week_usage }}
                </template>
              </el-table-column>
              <el-table-column label="建议补货" width="150">
                <template #default="{ row }">
                  <el-tag v-if="row.suggested_restock" type="warning">补 {{ row.suggested_restock }} {{ row.unit }}</el-tag>
                  <span v-else>--</span>
                </template>
              </el-table-column>
            </el-table>
          </template>
        </el-alert>
        <div class="warning-table-wrapper">
          <el-table :data="lowStockList" size="small" border>
            <el-table-column prop="name" label="药品" min-width="160" />
            <el-table-column prop="unit" label="单位" width="90" />
            <el-table-column prop="stock" label="库存" width="110">
              <template #default="{ row }">
                <el-tag type="danger">{{ row.stock }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="近30天用量" width="140">
              <template #default="{ row }">
                {{ row.usage_30d || 0 }}
              </template>
            </el-table-column>
            <el-table-column label="预计7天用量" width="140">
              <template #default="{ row }">
                {{ row.expected_week_usage }}
              </template>
            </el-table-column>
            <el-table-column label="建议补货" width="170">
              <template #default="{ row }">
                <el-tag v-if="row.suggested_restock" type="warning">补 {{ row.suggested_restock }} {{ row.unit }}</el-tag>
                <span v-else>--</span>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
      <div v-else>
        <el-alert
          title="库存充足"
          type="success"
          show-icon
          description="目前暂无需要警报的药品"
        />
      </div>
    </el-card>

    <el-card>
      <template #header>
        <div class="card-header">
          <span>新增药品</span>
          <small>录入新的药品品类并设置基础信息</small>
        </div>
      </template>
      <el-form :model="createForm" label-width="90px">
        <el-row :gutter="16">
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="名称">
              <el-input v-model="createForm.name" placeholder="如 布洛芬缓释胶囊" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="单价">
              <el-input-number v-model="createForm.price" :min="0" :step="0.5" :precision="2" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="单位">
              <el-input v-model="createForm.unit" placeholder="盒/瓶/支" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="初始库存">
              <el-input-number v-model="createForm.stock" :min="0" :precision="0" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16" class="form-actions-row" justify="end">
          <el-col :xs="24" :sm="12" :md="6" class="form-actions">
            <el-button type="primary" :loading="createLoading" @click="submitCreate">新增药品</el-button>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <el-card>
      <template #header>
        <div class="card-header">
          <span>采购药品</span>
          <small>补充库存，数量会自动累加到当前库存</small>
        </div>
      </template>
      <el-form :model="purchaseForm" label-width="90px">
        <el-row :gutter="16" align="middle" class="form-actions-row">
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="药品">
              <el-select v-model="purchaseForm.medicine_id" placeholder="请选择药品">
                <el-option
                  v-for="med in medicines"
                  :key="med.medicine_id"
                  :label="`${med.name} (${med.unit})`"
                  :value="med.medicine_id"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="采购量">
              <el-input-number v-model="purchaseForm.quantity" :min="1" :precision="0" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="24" :md="6" :offset="6" class="form-actions">
            <el-button type="primary" :loading="purchaseLoading" @click="submitPurchase">立即采购</el-button>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <el-card>
      <template #header>
        <div class="card-header card-header--row">
          <div>
            <span>药品库存</span>
            <small>结合近 {{ usageWindowDays }} 天用量给出 {{ planningHorizonDays }} 天补货建议</small>
          </div>
          <el-button
            type="warning"
            plain
            :loading="restockLoading"
            :disabled="!needsRestockCount"
            @click="handleReplenish"
          >
            一键补足{{ planningHorizonDays }}天库存
            <span v-if="needsRestockCount"> ({{ needsRestockCount }})</span>
          </el-button>
        </div>
      </template>
      <el-table :data="medicines" border>
        <el-table-column prop="name" label="名称" min-width="160" />
        <el-table-column prop="unit" label="单位" width="90" />
        <el-table-column prop="price" label="单价" width="110">
          <template #default="{ row }">￥{{ row.price.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="stock" label="库存" width="110">
          <template #default="{ row }">
            <el-tag :type="row.needs_restock || row.stock < lowStockThreshold ? 'danger' : 'success'">{{ row.stock }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="近30天用量" width="140">
          <template #default="{ row }">
            {{ row.usage_30d || 0 }}
          </template>
        </el-table-column>
        <el-table-column label="日均/预计" width="180">
          <template #default="{ row }">
            <div class="usage-cell usage-cell--clickable" @click="openTrendDialog(row)">
              <span>日均 {{ row.avg_daily_usage ? row.avg_daily_usage.toFixed(2) : '0.00' }}</span>
              <span>七天 {{ row.expected_week_usage }}</span>
              <span class="usage-cell__link">查看用量详情</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="建议补货" width="150">
          <template #default="{ row }">
            <el-tag v-if="row.suggested_restock" type="warning">补 {{ row.suggested_restock }} {{ row.unit }}</el-tag>
            <span v-else>--</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog
      v-model="trendDialogVisible"
      :title="trendMedicine ? `${trendMedicine.name} · 用量趋势` : '用量趋势'"
      width="720px"
    >
      <div v-if="displayTrendData.length" ref="trendChartRef" class="trend-chart">
        <div class="trend-chart__toolbar">
          <span class="trend-chart__title">{{ trendMode === 'monthly' ? '近12个月用量' : '近30天用量' }}</span>
          <div class="trend-chart__actions">
            <el-button-group size="small">
              <el-button :type="trendMode === 'daily' ? 'primary' : 'default'" @click="trendMode = 'daily'">近30天</el-button>
              <el-button :type="trendMode === 'monthly' ? 'primary' : 'default'" @click="trendMode = 'monthly'">近12个月</el-button>
            </el-button-group>
            <div class="trend-chart__export">
              <el-button size="small" type="success" plain @click="exportTrendPdf">导出 PDF</el-button>
            </div>
          </div>
        </div>
        <div class="trend-chart__body" ref="trendChartContentRef">
          <div class="trend-chart__grid">
            <div class="trend-chart__bars" :style="{ gridTemplateColumns: getGridColumns() }">
              <div
                v-for="point in displayTrendData"
                :key="point.date"
                class="trend-bar"
                :style="{ height: getBarHeight(point.quantity) }"
              >
                <span class="trend-bar__value">{{ point.quantity }}</span>
              </div>
            </div>
            <div
              v-if="trendStats.avg"
              class="trend-chart__avg-line"
              :style="{ bottom: getAverageLinePosition() }"
            >
              平均 {{ trendStats.avg.toFixed(1) }}
            </div>
          </div>
          <div class="trend-chart__axis">
            <span>{{ displayTrendData[0].date }}</span>
            <span>最大 {{ trendStats.max }}</span>
            <span>{{ displayTrendData[displayTrendData.length - 1].date }}</span>
          </div>
        </div>
      </div>
      <div v-else class="trend-chart__empty">暂无 {{ trendMode === 'monthly' ? '12个月' : '30天' }} 用量数据</div>
      <template #footer>
        <el-button @click="trendDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import dayjs from "dayjs";
import html2canvas from "html2canvas";
import { jsPDF } from "jspdf";
import { fetchMedicines, purchaseMedicine, createMedicine, replenishMedicines, type MedicineItem, type UsagePoint } from "../../api/modules/pharmacy";

const medicines = ref<MedicineItem[]>([]);
const purchaseForm = reactive({
  medicine_id: undefined as number | undefined,
  quantity: 1
});
const createForm = reactive({
  name: "",
  price: 0,
  stock: 0,
  unit: ""
});
const purchaseLoading = ref(false);
const createLoading = ref(false);
const lowStockThreshold = 50;
const usageWindowDays = 30;
const planningHorizonDays = 7;
const restockLoading = ref(false);
const trendDialogVisible = ref(false);
const trendMedicine = ref<MedicineItem | null>(null);
const trendDailyData = ref<UsagePoint[]>([]);
const trendMonthlyData = ref<UsagePoint[]>([]);
const trendMode = ref<"daily" | "monthly">("daily");
const trendChartRef = ref<HTMLElement | null>(null);
const trendChartContentRef = ref<HTMLElement | null>(null);

const lowStockList = computed(() =>
  medicines.value.filter((med) => med.needs_restock || med.stock < lowStockThreshold)
);
const needsRestockCount = computed(() => medicines.value.filter((med) => med.suggested_restock > 0).length);
const displayTrendData = computed(() => (trendMode.value === "monthly" ? trendMonthlyData.value : trendDailyData.value));

const trendStats = computed(() => {
  if (!displayTrendData.value.length) {
    return { max: 0, avg: 0 };
  }
  const quantities = displayTrendData.value.map((p) => p.quantity);
  const max = Math.max(...quantities, 0);
  const avg = quantities.reduce((sum, val) => sum + val, 0) / displayTrendData.value.length;
  return { max, avg };
});

async function loadMedicines() {
  try {
    const { data } = await fetchMedicines();
    medicines.value = data;
  } catch (error: any) {
    console.error("loadMedicines error", error);
    ElMessage.error(error.response?.data?.detail ?? "获取药品列表失败");
  }
}

async function submitPurchase() {
  if (!purchaseForm.medicine_id) {
    ElMessage.warning("请选择要采购的药品");
    return;
  }
  if (!purchaseForm.quantity || purchaseForm.quantity <= 0) {
    ElMessage.warning("采购数量必须大于 0");
    return;
  }
  purchaseLoading.value = true;
  try {
    await purchaseMedicine({
      medicine_id: purchaseForm.medicine_id,
      quantity: purchaseForm.quantity
    });
    ElMessage.success("采购成功，库存已更新");
    purchaseForm.quantity = 1;
    await loadMedicines();
  } catch (error: any) {
    console.error("purchase error", error);
    ElMessage.error(error.response?.data?.detail ?? "采购失败");
  } finally {
    purchaseLoading.value = false;
  }
}

async function submitCreate() {
  if (!createForm.name.trim()) {
    ElMessage.warning("请填写药品名称");
    return;
  }
  if (!createForm.unit.trim()) {
    ElMessage.warning("请填写单位");
    return;
  }
  if (createForm.price < 0) {
    ElMessage.warning("单价不能为负数");
    return;
  }
  if (createForm.stock < 0) {
    ElMessage.warning("库存不能为负数");
    return;
  }
  createLoading.value = true;
  try {
    await createMedicine({
      name: createForm.name.trim(),
      price: createForm.price,
      stock: createForm.stock,
      unit: createForm.unit.trim()
    });
    ElMessage.success("新增药品成功");
    Object.assign(createForm, { name: "", price: 0, stock: 0, unit: "" });
    await loadMedicines();
  } catch (error: any) {
    console.error("create medicine error", error);
    ElMessage.error(error.response?.data?.detail ?? "新增药品失败");
  } finally {
    createLoading.value = false;
  }
}

async function handleReplenish() {
  if (!needsRestockCount.value) {
    ElMessage.success("所有药品库存已满足建议");
    return;
  }
  restockLoading.value = true;
  try {
    const { data } = await replenishMedicines();
    medicines.value = data;
    ElMessage.success("已根据用量建议补足库存");
  } catch (error: any) {
    console.error("replenish error", error);
    ElMessage.error(error.response?.data?.detail ?? "补足库存失败");
  } finally {
    restockLoading.value = false;
  }
}

function openTrendDialog(medicine: MedicineItem) {
  trendMedicine.value = medicine;
  trendDailyData.value = medicine.usage_trend ?? [];
  trendMonthlyData.value = medicine.usage_monthly ?? [];
  trendMode.value = "daily";
  trendDialogVisible.value = true;
}

function getBarHeight(quantity: number) {
  const max = trendStats.value.max || 1;
  const ratio = quantity / max;
  return `${Math.max(ratio * 100, 4)}%`;
}

function getAverageLinePosition() {
  const max = trendStats.value.max || 1;
  if (!trendStats.value.avg) return "0%";
  const ratio = trendStats.value.avg / max;
  return `${Math.min(Math.max(ratio * 100, 0), 100)}%`;
}

function getGridColumns() {
  const count = displayTrendData.value.length || 1;
  return `repeat(${count}, minmax(6px, 1fr))`;
}

async function captureChartCanvas() {
  if (!trendChartContentRef.value || !displayTrendData.value.length) {
    ElMessage.warning("暂无可导出的图表");
    return null;
  }
  return html2canvas(trendChartContentRef.value, { backgroundColor: "#ffffff", scale: 2 });
}

async function exportTrendPdf() {
  const canvas = await captureChartCanvas();
  if (!canvas) return;

  const imgData = canvas.toDataURL("image/png");
  const pdf = new jsPDF({ orientation: "landscape", unit: "mm", format: "a4" });
  const pageWidth = pdf.internal.pageSize.getWidth();
  const pageHeight = pdf.internal.pageSize.getHeight();
  const margin = 10;
  const availableWidth = pageWidth - margin * 2;
  const availableHeight = pageHeight - margin * 2;
  const pxToMm = 25.4 / 96; // assuming 96 dpi
  const imgWidthMm = canvas.width * pxToMm;
  const imgHeightMm = canvas.height * pxToMm;
  const scale = Math.min(availableWidth / imgWidthMm, availableHeight / imgHeightMm, 1);
  const renderWidth = imgWidthMm * scale;
  const renderHeight = imgHeightMm * scale;
  const offsetX = (pageWidth - renderWidth) / 2;
  const offsetY = (pageHeight - renderHeight) / 2;

  pdf.addImage(imgData, "PNG", offsetX, offsetY, renderWidth, renderHeight, undefined, "FAST");

  const name = trendMedicine.value?.name ? trendMedicine.value.name.replace(/\s+/g, "-") : "medicine";
  const mode = trendMode.value === "monthly" ? "12m" : "30d";
  const filename = `${name}-${mode}用量分析-${dayjs().format("YYYYMMDD-HHmmss")}.pdf`;
  pdf.save(filename);
}

onMounted(loadMedicines);
</script>

<style scoped>
.pharmacy-board {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-header--row {
  flex-direction: row;
  justify-content: space-between;
  align-items: center;
}

.card-header--row > div {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.warning-card {
  border: 1px dashed #f0ad4e;
}

.warning-list {
  margin: 0;
  padding-left: 18px;
}

.warning-table-wrapper {
  margin-top: 12px;
}

.form-actions {
  display: flex;
  justify-content: flex-end;
}

.form-actions-row {
  margin-top: 4px;
}

.usage-cell {
  display: flex;
  flex-direction: column;
  font-size: 12px;
  line-height: 1.3;
  color: #606266;
}

.usage-cell span + span {
  margin-top: 2px;
}

.usage-cell--clickable {
  cursor: pointer;
  color: #303133;
}

.usage-cell__link {
  color: #409eff;
  font-size: 12px;
}

.trend-chart {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.trend-chart__toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.trend-chart__title {
  color: #606266;
  font-size: 13px;
}

.trend-chart__actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.trend-chart__export {
  display: flex;
  gap: 6px;
}

.trend-chart__body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.trend-chart__grid {
  position: relative;
  border: 1px solid #ebeef5;
  padding: 16px 12px 8px;
  border-radius: 8px;
  background: #fff;
}

.trend-chart__bars {
  display: grid;
  grid-template-columns: repeat(30, minmax(6px, 1fr));
  gap: 4px;
  align-items: end;
  height: 220px;
}

.trend-bar {
  position: relative;
  background: linear-gradient(180deg, #66b1ff, #409eff);
  border-radius: 2px 2px 0 0;
}

.trend-bar__value {
  position: absolute;
  top: -18px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 10px;
  color: #909399;
}

.trend-chart__avg-line {
  position: absolute;
  left: 8px;
  right: 8px;
  border-top: 1px dashed #f56c6c;
  color: #f56c6c;
  font-size: 12px;
  padding-top: 4px;
}

.trend-chart__axis {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #909399;
}

.trend-chart__empty {
  padding: 24px;
  text-align: center;
  color: #909399;
}
</style>
