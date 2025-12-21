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

    <el-dialog
      v-if="auth.isHeadNurse"
      v-model="overdueVisible"
      title="过期待办提醒"
      width="560px"
      :close-on-click-modal="false"
    >
      <el-alert title="以下代办已过期，请尽快处理" type="warning" :closable="false" show-icon />
      <div class="overdue-list" v-loading="overdueLoading">
        <div v-for="task in overdueTasks" :key="task.task_id" class="overdue-item">
          <div class="overdue-meta">
            <span>{{ task.patient_name }} · {{ task.type }}</span>
            <small>{{ formatTime(task.time) }} · {{ task.nurse_name }}</small>
          </div>
          <el-button
            type="danger"
            size="small"
            :loading="overdueHandleId === task.task_id"
            @click="handleOverdue(task.task_id)"
          >处理</el-button>
        </div>
        <el-empty v-if="!overdueTasks.length && !overdueLoading" description="暂无过期待办" />
      </div>
      <template #footer>
        <el-button @click="overdueVisible = false">稍后处理</el-button>
        <el-button type="primary" @click="loadOverdueTasks(false)">刷新列表</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import dayjs from "dayjs";
import { fetchMySchedules, fetchTodayTasks, completeTask, type NurseScheduleItem, type TodayTaskItem } from "../../api/modules/nurse";
import { useAuthStore } from "../../stores/auth";
import { ElMessage } from "element-plus";
import { addIgnoredExpiredTaskId, loadIgnoredExpiredTaskIds } from "../../utils/ignoredTasks";

const schedules = ref<NurseScheduleItem[]>([]);
const loading = ref(false);
const taskLoading = ref(false);
const todayTasks = ref<TodayTaskItem[]>([]);
const overdueVisible = ref(false);
const overdueLoading = ref(false);
const overdueTasks = ref<TodayTaskItem[]>([]);
const overdueHandleId = ref<number | null>(null);
const dueSoonCount = computed(() => todayTasks.value.filter(t => t.status === "未完成" && dayjs(t.time).diff(dayjs(), "minute") <= 120 && dayjs(t.time).diff(dayjs(), "minute") >= 0).length);
const overdueCount = computed(() => todayTasks.value.filter(t => t.status === "已过期").length);
const pendingCount = computed(() => todayTasks.value.filter(t => t.status === "未完成").length);
const router = useRouter();
const auth = useAuthStore();

function statusRank(status: string) {
  if (status === "未完成") return 0;
  if (status === "已过期") return 1;
  return 2;
}

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
    const ignored = loadIgnoredExpiredTaskIds();
    todayTasks.value = data
      .filter((t) => !(t.status === "已过期" && ignored.has(t.task_id)))
      .slice()
      .sort((a, b) => {
        const rankDiff = statusRank(a.status) - statusRank(b.status);
        if (rankDiff !== 0) return rankDiff;
        return dayjs(a.time).valueOf() - dayjs(b.time).valueOf();
      });
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail ?? "加载今日待办失败");
  } finally {
    taskLoading.value = false;
  }
}

async function loadOverdueTasks(autoOpen = true) {
  if (!auth.isHeadNurse) return;
  overdueLoading.value = true;
  try {
    const { data } = await fetchTodayTasks();
    const ignored = loadIgnoredExpiredTaskIds();
    overdueTasks.value = data
      .filter((t) => t.status === "已过期" && !ignored.has(t.task_id))
      .sort((a, b) => dayjs(a.time).valueOf() - dayjs(b.time).valueOf());
    if (autoOpen && overdueTasks.value.length) {
      overdueVisible.value = true;
    }
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail ?? "加载过期待办失败");
  } finally {
    overdueLoading.value = false;
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

async function handleOverdue(taskId: number) {
  if (!auth.isHeadNurse) return;
  overdueHandleId.value = taskId;
  try {
    await completeTask(taskId);
    addIgnoredExpiredTaskId(taskId);
    overdueTasks.value = overdueTasks.value.filter((t) => t.task_id !== taskId);
    await loadTodayTasks();
    if (!overdueTasks.value.length) {
      overdueVisible.value = false;
    }
    ElMessage.success("已处理该过期待办");
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail ?? "处理失败");
  } finally {
    overdueHandleId.value = null;
  }
}

function goManage() {
  router.push("/workspace/nurse/schedule-management");
}

onMounted(() => {
  void loadSchedules();
  void loadTodayTasks();
  if (auth.isHeadNurse) {
    void loadOverdueTasks();
  }
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

.overdue-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.overdue-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  border: 1px solid #fde2e2;
  border-radius: 6px;
  background: #fff7f5;
}

.overdue-meta {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #d4380d;
}
</style>
