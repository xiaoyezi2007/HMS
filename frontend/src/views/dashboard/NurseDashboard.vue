<template>
  <div class="nurse-board">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>我的排班</span>
          <small>按病房类型汇总，当班护士可快速浏览任务</small>
        </div>
      </template>
      <el-table :data="schedules" v-loading="loading" empty-text="暂无排班数据">
        <el-table-column prop="schedule_id" label="排班编号" width="120" />
        <el-table-column prop="ward_type" label="病房类型" width="160" />
        <el-table-column prop="time" label="值班时间">
          <template #default="scope">
            {{ formatTime(scope.row.time) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import dayjs from "dayjs";
import { fetchMySchedules, type NurseScheduleItem } from "../../api/modules/nurse";

const schedules = ref<NurseScheduleItem[]>([]);
const loading = ref(false);

function formatTime(value: string) {
  return dayjs(value).format("YYYY-MM-DD HH:mm");
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
  flex-direction: column;
}

.card-header small {
  color: #94a3b8;
}
</style>
