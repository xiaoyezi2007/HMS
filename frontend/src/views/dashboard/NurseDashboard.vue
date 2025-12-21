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

    <el-card>
      <template #header>
        <div class="card-header">
          <div class="card-title">
            <div class="title-line">
              <span>今日待办</span>
              <el-tag type="info" effect="light" size="small">{{ todayTasks.length }} 条</el-tag>
              <el-tag v-if="overdueCount" type="danger" effect="dark" size="small">已过期 {{ overdueCount }} 条</el-tag>
              <el-tag v-else-if="dueSoonCount" type="warning" effect="light" size="small">2小时内 {{ dueSoonCount }} 条</el-tag>
              <el-tag v-if="auth.isHeadNurse && pendingCount" type="warning" effect="plain" size="small">未完成 {{ pendingCount }} 条</el-tag>
            </div>
            <small v-if="auth.isHeadNurse">护士长可查看全部今日任务</small>
            <small v-else>仅显示分配给我的今日任务</small>
          </div>
          <div class="card-actions">
            <el-button size="small" :loading="taskLoading" @click="loadTodayTasks">刷新</el-button>
          </div>
        </div>
      </template>
      <el-table
        :data="todayTasks"
        :row-class-name="taskRowClass"
        v-loading="taskLoading"
        empty-text="今日无待办"
        :default-sort="{ prop: 'time', order: 'ascending' }"
      >
        <el-table-column prop="patient_name" label="患者" min-width="140" />
        <el-table-column prop="type" label="代办项目" min-width="120" />
        <el-table-column prop="time" label="预计完成时间" min-width="180" sortable>
          <template #default="scope">
            <span :class="{ 'time-alert': isDueSoon(scope.row) }">{{ formatTime(scope.row.time) }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="110">
          <template #default="scope">
            <el-tag :type="statusType(scope.row)" effect="plain">{{ scope.row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="nurse_name" label="护士" width="120" v-if="auth.isHeadNurse" />
        <el-table-column label="操作" width="120" fixed="right">
          <template #default="scope">
            <el-button
              size="small"
              type="primary"
              link
              :disabled="scope.row.status !== '未完成'"
              @click="complete(scope.row.task_id)"
            >完成</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import dayjs from "dayjs";
import { fetchMySchedules, fetchTodayTasks, completeTask, type NurseScheduleItem, type TodayTaskItem } from "../../api/modules/nurse";
import { useAuthStore } from "../../stores/auth";
import { ElMessage } from "element-plus";

const schedules = ref<NurseScheduleItem[]>([]);
const loading = ref(false);
const taskLoading = ref(false);
const todayTasks = ref<TodayTaskItem[]>([]);
const dueSoonCount = computed(() => todayTasks.value.filter(t => t.status === "未完成" && dayjs(t.time).diff(dayjs(), "minute") <= 120 && dayjs(t.time).diff(dayjs(), "minute") >= 0).length);
const overdueCount = computed(() => todayTasks.value.filter(t => t.status === "已过期").length);
const pendingCount = computed(() => todayTasks.value.filter(t => t.status === "未完成").length);
const router = useRouter();
const auth = useAuthStore();

function formatRange(start: string, end: string) {
  return `${dayjs(start).format("YYYY-MM-DD HH:mm")} ~ ${dayjs(end).format("HH:mm")}`;
}

function formatTime(val: string) {
  return dayjs(val).format("YYYY-MM-DD HH:mm");
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

async function loadTodayTasks() {
  taskLoading.value = true;
  try {
    const { data } = await fetchTodayTasks();
    todayTasks.value = data;
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail ?? "加载今日待办失败");
  } finally {
    taskLoading.value = false;
  }
}

function statusType(row: TodayTaskItem) {
  if (row.status === "已完成") return "success";
  if (row.status === "已过期") return "danger";
  return "warning";
}

function taskRowClass({ row }: { row: TodayTaskItem }) {
  if (row.status === "已过期") return "task-expired";
  if (row.status === "未完成") {
    const diff = dayjs(row.time).diff(dayjs(), "minute");
    if (diff <= 120) return "task-alert";
  }
  return "";
}

function isDueSoon(row: TodayTaskItem) {
  if (row.status !== "未完成") return false;
  const diff = dayjs(row.time).diff(dayjs(), "minute");
  return diff <= 120;
}

async function complete(taskId: number) {
  try {
    await completeTask(taskId);
    ElMessage.success("已标记完成");
    await loadTodayTasks();
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail ?? "操作失败");
  }
}

function goManage() {
  router.push("/workspace/nurse/schedule-management");
}

onMounted(() => {
  void loadSchedules();
  void loadTodayTasks();
});
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

.title-line {
  display: flex;
  align-items: center;
  gap: 8px;
}

.title-line .el-tag {
  line-height: 18px;
}

.card-header small {
  color: #94a3b8;
}

.card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-alert td {
  background-color: #fff1f0 !important;
}

.task-expired td {
  background-color: #ffece0 !important;
}

.time-alert {
  color: #cf1322;
  font-weight: 600;
}
</style>
