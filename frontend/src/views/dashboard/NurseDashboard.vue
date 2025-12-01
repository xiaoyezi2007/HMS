<template>
  <div class="nurse-board">
    <el-card>
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <span>我的排班</span>
            <small>按病房类型汇总，当班护士可快速浏览任务</small>
          </div>
          <el-button v-if="auth.isHeadNurse" size="small" type="primary" @click="goManage">排班管理</el-button>
        </div>
      </template>
      <el-table :data="schedules" v-loading="loading" empty-text="暂无排班数据">
        <el-table-column prop="schedule_id" label="排班编号" width="120" />
        <el-table-column prop="ward_type" label="病房类型" width="160" />
        <el-table-column prop="start_time" label="值班时间">
          <template #default="scope">
            {{ formatRange(scope.row.start_time, scope.row.end_time) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import dayjs from "dayjs";
import { fetchMySchedules, type NurseScheduleItem } from "../../api/modules/nurse";
import { useAuthStore } from "../../stores/auth";

const schedules = ref<NurseScheduleItem[]>([]);
const loading = ref(false);
const router = useRouter();
const auth = useAuthStore();

function formatRange(start: string, end: string) {
  return `${dayjs(start).format("YYYY-MM-DD HH:mm")} ~ ${dayjs(end).format("HH:mm")}`;
}

async function loadSchedules() {
  loading.value = true;
  try {
    const { data } = await fetchMySchedules();
    schedules.value = data;
  } finally {
    loading.value = false;
  }
}

function goManage() {
  router.push("/workspace/nurse/schedule-management");
}

onMounted(loadSchedules);
</script>

<style scoped>
.nurse-board {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.card-title {
  display: flex;
  flex-direction: column;
}

.card-header small {
  color: #94a3b8;
}
</style>
