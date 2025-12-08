<template>
  <div class="pharmacy-board">
    <el-card class="warning-card">
      <template #header>
        <div class="card-header">
          <span>库存预警</span>
          <small>低于 {{ lowStockThreshold }} 的药品会在此处提示</small>
        </div>
      </template>
      <div v-if="lowStockList.length">
        <el-alert
          title="以下药品库存较低，建议立即采购"
          type="warning"
          show-icon
          :closable="false"
        >
          <template #description>
            <el-table :data="lowStockList" size="mini" stripe>
              <el-table-column prop="name" label="药品" />
              <el-table-column prop="stock" label="库存" width="120">
                <template #default="{ row }">
                  <el-tag type="danger">{{ row.stock }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="unit" label="单位" width="100" />
              <el-table-column prop="expire_date" label="有效期" width="130" />
            </el-table>
          </template>
        </el-alert>
        <div class="warning-table-wrapper">
          <el-table :data="lowStockList" size="small" border>
            <el-table-column prop="name" label="药品" />
            <el-table-column prop="stock" label="库存" width="120">
              <template #default="{ row }">
                <el-tag type="danger">{{ row.stock }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="unit" label="单位" width="100" />
            <el-table-column prop="expire_date" label="有效期" width="130" />
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
          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="名称">
              <el-input v-model="createForm.name" placeholder="如 布洛芬缓释胶囊" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="单位">
              <el-input v-model="createForm.unit" placeholder="盒/瓶/支" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="5">
            <el-form-item label="单价">
              <el-input-number v-model="createForm.price" :min="0" :step="0.5" :precision="2" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="5">
            <el-form-item label="初始库存">
              <el-input-number v-model="createForm.stock" :min="0" :precision="0" />
            </el-form-item>
          </el-col>
        </el-row>
        <el-row :gutter="16" align="middle">
          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="有效期">
              <el-date-picker
                v-model="createForm.expire_date"
                type="date"
                placeholder="选择日期"
                value-format="YYYY-MM-DD"
              />
            </el-form-item>
          </el-col>
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
      <el-form :model="purchaseForm" label-width="80px">
        <el-row :gutter="16" align="middle">
          <el-col :xs="24" :sm="12" :md="10">
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
          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="采购量">
              <el-input-number v-model="purchaseForm.quantity" :min="1" :precision="0" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="24" :md="6" class="form-actions">
            <el-button type="primary" :loading="purchaseLoading" @click="submitPurchase">立即采购</el-button>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <el-card>
      <template #header>
        <div class="card-header">
          <span>药品库存</span>
          <small>实时反映库存数量与有效期</small>
        </div>
      </template>
      <el-table :data="medicines" border>
        <el-table-column prop="name" label="名称" />
        <el-table-column prop="unit" label="单位" width="100" />
        <el-table-column prop="price" label="单价" width="120">
          <template #default="{ row }">￥{{ row.price.toFixed(2) }}</template>
        </el-table-column>
        <el-table-column prop="stock" label="库存" width="120">
          <template #default="{ row }">
            <el-tag :type="row.stock < lowStockThreshold ? 'danger' : 'success'">{{ row.stock }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="expire_date" label="有效期" width="160" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import { fetchMedicines, purchaseMedicine, createMedicine, type MedicineItem } from "../../api/modules/pharmacy";

const medicines = ref<MedicineItem[]>([]);
const purchaseForm = reactive({
  medicine_id: undefined as number | undefined,
  quantity: 1
});
const createForm = reactive({
  name: "",
  price: 0,
  stock: 0,
  unit: "",
  expire_date: ""
});
const purchaseLoading = ref(false);
const createLoading = ref(false);
const lowStockThreshold = 50;

const lowStockList = computed(() => medicines.value.filter((med) => med.stock < lowStockThreshold));

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
  if (!createForm.expire_date) {
    ElMessage.warning("请选择有效期");
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
      unit: createForm.unit.trim(),
      expire_date: createForm.expire_date
    });
    ElMessage.success("新增药品成功");
    Object.assign(createForm, { name: "", price: 0, stock: 0, unit: "", expire_date: "" });
    await loadMedicines();
  } catch (error: any) {
    console.error("create medicine error", error);
    ElMessage.error(error.response?.data?.detail ?? "新增药品失败");
  } finally {
    createLoading.value = false;
  }
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
</style>
