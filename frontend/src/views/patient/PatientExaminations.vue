<template>
  <div class="patient-module">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>检查结果查询</span>
        </div>
      </template>
      <div>
        <div v-if="loading" style="text-align:center; padding:16px"><el-spin /></div>
        <div v-else>
          <el-table v-if="exams.length" :data="exams" stripe style="width:100%">
            <el-table-column prop="exam_id" label="检查号" width="100" />
            <el-table-column prop="type" label="检查类型" />
            <el-table-column prop="result" label="结果" width="120" />
            <el-table-column prop="date" label="时间" width="180">
              <template #default="{ row }">{{ new Date(row.date).toLocaleString() }}</template>
            </el-table-column>
            <!-- 病历ID 不再显示 -->
            <el-table-column prop="reg_id" label="挂号ID" width="100" />
          </el-table>
          <el-empty v-else description="暂无检查结果" />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { fetchPatientExaminations } from "../../api/modules/patient";

const exams = ref<any[]>([]);
const loading = ref(true);

async function loadExams() {
  loading.value = true;
  try {
    const res = await fetchPatientExaminations();
    exams.value = res.data ?? [];
  } catch (err) {
    console.error("fetchPatientExaminations error", err);
    exams.value = [];
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  loadExams();
});
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
}
</style>
