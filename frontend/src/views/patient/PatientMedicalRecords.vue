<template>
  <div class="patient-module">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>我的病历</span>
          <small>查看医生为你书写的病历记录</small>
        </div>
      </template>
      <div>
        <el-table v-if="!loading && records.length" :data="records" style="width: 100%" :row-class-name="rowClassName">
          <el-table-column prop="create_time" label="时间" width="180" />
          <el-table-column prop="complaint" label="主诉" />
          <el-table-column prop="diagnosis" label="诊断" />
          <el-table-column prop="suggestion" label="建议" />
          <el-table-column prop="reg_id" label="挂号ID" width="120" />
        </el-table>

        <el-empty v-else-if="!loading && !records.length" description="暂无病历记录" />

        <div v-else style="text-align:center; padding:16px">
          <el-spin />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { fetchMyMedicalRecords, MedicalRecordItem } from "../../api/modules/patient";

const records = ref<MedicalRecordItem[]>([]);
const loading = ref(true);
const route = useRoute();
const highlightRegId = Number(route.query.reg_id || 0) || null;

function rowClassName({ row }: { row: MedicalRecordItem }) {
  if (!highlightRegId) return "";
  return row.reg_id === highlightRegId ? "highlighted" : "";
}

async function load() {
  loading.value = true;
  try {
    const res = await fetchMyMedicalRecords();
    // axios response 包装可能为 res.data
    records.value = res.data ?? [];
  } catch (err) {
    console.error("fetchMyMedicalRecords error", err);
    records.value = [];
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  load();
});
</script>

<style scoped>
.card-header {
  display: flex;
  flex-direction: column;
}
.card-header small {
  color: #94a3b8;
}

.highlighted {
  background: #fff7cc !important;
}
</style>
