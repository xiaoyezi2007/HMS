<template>
  <div class="doctor-prescription">
    <el-card>
      <h3>{{ prescriptionTitle }}</h3>
    </el-card>

    <el-card class="mt-3">
      <div v-if="medLoading" style="text-align:center; padding:20px"><el-spin /></div>
      <div v-else>
        <el-form label-width="80px">
          <el-form-item label="药品">
            <el-button type="primary" @click="openMedDialog">从药品表选择</el-button>

            

            <teleport to="body">
              <div v-if="medDialogVisible" class="custom-modal-overlay" @click.self="medDialogVisible = false">
                <div class="custom-modal" role="dialog" aria-label="选择药品（可多选）">
                  <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:12px">
                    <div style="font-size:16px; font-weight:700">选择药品（可多选）</div>
                    <div>
                      <el-button size="small" @click="medDialogVisible = false">关闭</el-button>
                    </div>
                  </div>
                  <div style="margin-bottom:8px; display:flex; gap:8px; align-items:center">
                    <el-input v-model="medSearch" placeholder="按名称搜索" clearable style="width:280px" />
                    <el-button size="small" @click="clearMedSearch">清除</el-button>
                  </div>
                  <div v-if="medLoading" style="text-align:center; padding:20px"><el-spin /></div>
                  <div v-else-if="!filteredMedicines.length" style="text-align:center; padding:20px">暂无药品数据</div>
                  <div v-else>
                    <el-table
                      ref="medTableRef"
                      :data="paginatedMedicines"
                      style="width:100%"
                      stripe
                      :row-key="row => row.medicine_id"
                      :reserve-selection="true"
                      @selection-change="onSelectionChange"
                    >
                      <el-table-column type="selection" width="55" />
                      <el-table-column prop="name" label="名称" />
                      <el-table-column prop="price" label="价格(¥)" width="120" />
                      <el-table-column prop="stock" label="库存" width="100" />
                      <el-table-column prop="unit" label="单位" width="100" />
                      <el-table-column label="数量" width="200" align="center">
                        <template #default="{ row }">
                          <el-input-number v-model="medSettings[row.medicine_id].quantity" :min="1" controls-position="right" style="width:120px;" />
                        </template>
                      </el-table-column>
                      <el-table-column label="用法" width="320">
                        <template #default="{ row }">
                          <el-input v-model="medSettings[row.medicine_id].usage" placeholder="用法 / 频次" />
                        </template>
                      </el-table-column>
                    </el-table>
                    <div style="display:flex; justify-content:flex-end; margin-top:8px">
                      <el-pagination
                        layout="prev, pager, next, jumper"
                        :total="filteredMedicines.length"
                        :page-size="pageSize"
                        v-model:current-page="currentPage"
                        small
                        hide-on-single-page
                      />
                    </div>
                  </div>
                  <div style="display:flex; justify-content:flex-end; gap:8px; margin-top:12px">
                    <el-button @click="medDialogVisible = false">取消</el-button>
                    <el-button type="primary" @click="addSelectedToItems">加入处方</el-button>
                  </div>
                </div>
              </div>
            </teleport>
          </el-form-item>

          <el-table :data="items" stripe style="width:100%">
            <el-table-column prop="name" label="药品" />
            <el-table-column label="数量" width="140" align="center">
              <template #default="{ row }">
                <el-input-number v-model="row.quantity" :min="1" controls-position="right" style="width:110px" />
              </template>
            </el-table-column>
            <el-table-column label="用法" width="300">
              <template #default="{ row }">
                <el-input v-model="row.usage" placeholder="用法 / 频次" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="scope">
                <el-button type="text" @click="removeItem(scope.$index)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-form-item>
            <el-button type="primary" :loading="submitting" @click="submitPrescription">提交处方</el-button>
            <el-button @click="cancel" style="margin-left:8px">取消</el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onActivated, computed, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { fetchMedicines, createPrescription, fetchPrescriptionByRecord } from "../../api/modules/pharmacy";
import { fetchMedicalRecordByReg, submitMedicalRecord, fetchConsultationInfo, startHandling } from "../../api/modules/doctor";

const route = useRoute();
const router = useRouter();
const regId = Number(route.params.reg_id || route.query.reg_id || 0);

const prescriptionTitle = computed(() => {
  const name = patient.value?.name;
  return name ? `为患者 ${name} 开具处方` : "为患者开具处方";
});

const medicines = ref<any[]>([]);
const medLoading = ref(true);

const medDialogVisible = ref(false);
const medTableRef = ref();
const selectedRows = ref<any[]>([]);
const selectedIds = ref<Set<number>>(new Set());
const medSearch = ref<string>("");
const medSettings = ref<Record<number, { quantity: number; usage: string }>>({});
const items = ref<Array<{ medicine_id: number; name: string; quantity: number; usage: string }>>([]);
const record = ref<any>(null);
const currentPage = ref(1);
const pageSize = ref(6);

async function loadExistingPrescriptionForRecord(recordId: number) {
  try {
    const { data } = await fetchPrescriptionByRecord(recordId);
    // populate items and medSettings
    items.value = data.details.map((d: any) => ({ medicine_id: d.medicine_id, name: d.medicine_name || d.medicine_id, quantity: d.quantity, usage: d.usage }));
    for (const it of items.value) {
      if (!medSettings.value[it.medicine_id]) medSettings.value[it.medicine_id] = { quantity: it.quantity || 1, usage: it.usage || "" };
    }
  } catch (e: any) {
    // 404 (no prescription) is fine; other errors show a message
    if (e?.response?.status && e.response.status !== 404) {
      console.error("加载已有处方失败", e);
      ElMessage.error(e?.response?.data?.detail ?? "加载已有处方失败");
    }
  }
}

const submitting = ref(false);
const patient = ref<any>(null);

async function loadMedicines() {
  medLoading.value = true;
  try {
    const { data } = await fetchMedicines({ includeStats: false });
    medicines.value = data;
    // 初始化 medSettings，确保每行的 quantity/usage 可绑定
    const map: Record<number, { quantity: number; usage: string }> = {};
    for (const m of data) {
      map[m.medicine_id] = { quantity: 1, usage: "" };
    }
    medSettings.value = map;
  } catch (err: any) {
    ElMessage.error("获取药品列表失败");
  } finally {
    medLoading.value = false;
  }
}

async function loadPatientInfo() {
  try {
    const { data } = await fetchConsultationInfo(regId);
    patient.value = data.patient;
    // try to load medical record and existing prescription
    try {
      const { data: rec } = await fetchMedicalRecordByReg(regId);
      record.value = rec;
      // load prescription for this record if any
      await loadExistingPrescriptionForRecord(rec.record_id);
    } catch (err: any) {
      // no record yet is expected; ignore 404
      if (!(err?.response?.status === 404)) console.warn("获取病历信息时出错", err);
    }
  } catch (err) {
    // ignore
  }
}

function openMedDialog() {
  medDialogVisible.value = true;
}

function onSelectionChange(rows: any[]) {
  const pageIds = new Set((rows || []).map((r: any) => r.medicine_id));
  // 同步当前页的选择到全局选择集合
  for (const med of paginatedMedicines.value) {
    if (pageIds.has(med.medicine_id)) {
      selectedIds.value.add(med.medicine_id);
    } else {
      selectedIds.value.delete(med.medicine_id);
    }
  }
  // 更新全局已选行，确保数量/用法可编辑
  selectedRows.value = medicines.value.filter((m: any) => selectedIds.value.has(m.medicine_id));
  for (const m of selectedRows.value) {
    if (!medSettings.value[m.medicine_id]) {
      medSettings.value[m.medicine_id] = { quantity: 1, usage: "" };
    }
  }
}

// 支持按 ESC 关闭模态
watch(medDialogVisible, (val) => {
  function onKey(e: KeyboardEvent) {
    if (e.key === "Escape") medDialogVisible.value = false;
  }
  if (val) {
    document.addEventListener("keydown", onKey);
  } else {
    document.removeEventListener("keydown", onKey);
  }
});

function addSelectedToItems() {
  if (!selectedRows.value.length) {
    ElMessage.warning("请选择至少一种药品");
    return;
  }
  // 将选中的药品加入处方，使用 medSettings 中的数量与用法，避免重复
  for (const med of selectedRows.value) {
    const exists = items.value.find(i => i.medicine_id === med.medicine_id);
    const setting = medSettings.value[med.medicine_id] || { quantity: 1, usage: "" };
    if (!exists) {
      items.value.push({ medicine_id: med.medicine_id, name: med.name, quantity: setting.quantity, usage: setting.usage });
    }
  }
  // 重置并关闭对话框
  selectedIds.value.clear();
  selectedRows.value = [];
  medTableRef.value?.clearSelection();
  medDialogVisible.value = false;
}

function clearMedSearch() {
  medSearch.value = "";
}

const filteredMedicines = computed(() => {
  if (!medSearch.value) return medicines.value;
  const s = medSearch.value.trim().toLowerCase();
  return medicines.value.filter((m: any) => (m.name || "").toLowerCase().includes(s));
});

const paginatedMedicines = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  return filteredMedicines.value.slice(start, start + pageSize.value);
});

watch(filteredMedicines, (list) => {
  // 避免筛选后当前页超出范围
  const maxPage = Math.max(1, Math.ceil(list.length / pageSize.value));
  if (currentPage.value > maxPage) currentPage.value = 1;
});

watch(medSearch, () => {
  currentPage.value = 1;
});

function removeItem(idx: number) {
  items.value.splice(idx, 1);
}

function incrementMed(row: any) {
  const id = row.medicine_id;
  if (!medSettings.value[id]) medSettings.value[id] = { quantity: 1, usage: "" };
  medSettings.value[id].quantity = (medSettings.value[id].quantity || 1) + 1;
}

function decrementMed(row: any) {
  const id = row.medicine_id;
  if (!medSettings.value[id]) medSettings.value[id] = { quantity: 1, usage: "" };
  if ((medSettings.value[id].quantity || 1) > 1) medSettings.value[id].quantity -= 1;
}

async function submitPrescription() {
  if (!items.value.length) {
    ElMessage.warning("请先添加至少一项处方");
    return;
  }
  submitting.value = true;
  try {
    // 确保有病历：尝试获取病历，若无则自动创建一个最小病历
    let recordId: number | null = null;
    try {
      const { data } = await fetchMedicalRecordByReg(regId);
      recordId = data.record_id;
    } catch (e: any) {
      // 如果没有病历（404），自动创建一个简短病历
      if (e?.response?.status === 404) {
        const recPayload = { complaint: "（处方自动生成）", diagnosis: "（处方）", suggestion: "" };
        try {
          const { data: rec } = await submitMedicalRecord(regId, recPayload);
            recordId = rec.record_id;
            record.value = rec;
        } catch (err2: any) {
          // 如果因为未开始就诊导致创建病历失败，尝试先开始办理再重试一次
          if (err2?.response?.status === 400 || err2?.response?.status === 403) {
            try {
              await startHandling(regId);
              const { data: rec } = await submitMedicalRecord(regId, recPayload);
              recordId = rec.record_id;
              record.value = rec;
            } catch (err3: any) {
              throw err3;
            }
          } else {
            throw err2;
          }
        }
      } else {
        throw e;
      }
    }

    const presPayload = { record_id: recordId, items: items.value.map(i => ({ medicine_id: i.medicine_id, quantity: i.quantity, usage: i.usage })) };
    await createPrescription(presPayload);
    ElMessage.success("处方已提交");
    // reload existing prescription to reflect any server-side changes
    if (recordId) await loadExistingPrescriptionForRecord(recordId);
    router.push({ name: "consultation", params: { reg_id: String(regId) } });
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail ?? "提交处方失败");
  } finally {
    submitting.value = false;
  }
}

function cancel() {
  router.push({ name: "consultation", params: { reg_id: String(regId) } });
}

onMounted(async () => {
  await loadMedicines();
  await loadPatientInfo();
});

// 如果使用了 keep-alive 或页面在后台切换回来，确保重新加载病历和处方数据
onActivated(async () => {
  await loadPatientInfo();
});
</script>

<style scoped>
.mt-3 { margin-top: 16px; }

.custom-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 16px;
  overflow: auto;
}

.custom-modal {
  background: #fff;
  border-radius: 10px;
  padding: 16px 20px 14px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12);
  width: min(1100px, 100%);
  max-height: 80vh;
  overflow: auto;
}
</style>
