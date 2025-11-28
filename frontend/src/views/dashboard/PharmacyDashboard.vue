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
import { fetchMedicines, purchaseMedicine, type MedicineItem } from "../../api/modules/pharmacy";

const medicines = ref<MedicineItem[]>([]);
const purchaseForm = reactive({
  medicine_id: undefined as number | undefined,
  quantity: 1
});
const purchaseLoading = ref(false);
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
