<template>
  <div class="head-nurse-page">
    <el-card class="auto-card">
      <template #header>
        <div class="card-header">
          <div>
            <span>一键排班</span>
            <small>按时间段自动为所选病房生成排班，默认排除护士长</small>
          </div>
          <el-button type="primary" :loading="autoLoading" @click="handleAutoSchedule">一键排班</el-button>
        </div>
      </template>
      <el-form :inline="true" :model="autoForm" label-width="88px" class="auto-form">
        <el-form-item label="开始时间">
          <el-date-picker
            v-model="autoForm.start_time"
            type="datetime"
            placeholder="选择开始时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DDTHH:mm:ss"
          />
        </el-form-item>
        <el-form-item label="每班时长">
          <el-input-number v-model="autoForm.shift_hours" :min="1" :max="24" />
          <span class="unit">小时</span>
        </el-form-item>
        <el-form-item label="班次数量">
          <el-input-number v-model="autoForm.shift_count" :min="1" :max="24" />
          <span class="unit">个</span>
        </el-form-item>
        <el-form-item label="病房范围" class="wide-item">
          <div class="ward-range">
            <el-radio-group v-model="autoForm.range_mode" size="small">
              <el-radio-button label="all">全部</el-radio-button>
              <el-radio-button label="type">按类型</el-radio-button>
              <el-radio-button label="ward">按病房</el-radio-button>
            </el-radio-group>
            <el-select
              v-if="autoForm.range_mode === 'type'"
              v-model="autoForm.ward_types"
              multiple
              collapse-tags
              collapse-tags-tooltip
              placeholder="请选择病房类型"
              class="ward-select"
            >
              <el-option v-for="type in wardTypeOptions" :key="type" :label="type" :value="type" />
            </el-select>
            <el-select
              v-else-if="autoForm.range_mode === 'ward'"
              v-model="autoForm.ward_ids"
              multiple
              collapse-tags
              collapse-tags-tooltip
              placeholder="请选择病房"
              class="ward-select"
            >
              <el-option v-for="ward in context.wards" :key="ward.ward_id" :label="`${ward.ward_type} (#${ward.ward_id})`" :value="ward.ward_id" />
            </el-select>
          </div>
        </el-form-item>
      </el-form>
      <el-alert type="info" title="系统会轮换安排非护士长的账号，若需要特殊调整可在下方手动编辑" :closable="false" />
    </el-card>

    <el-card>
      <template #header>
        <div class="card-header">
          <div>
            <span>排班总览</span>
            <small>按病房与时间段展示，可编辑负责护士</small>
          </div>
          <el-button type="primary" size="small" @click="openCreateDialog">新增排班</el-button>
        </div>
      </template>
      <el-table :data="flattenedRows" v-loading="loading" empty-text="暂无排班数据" border>
        <el-table-column prop="ward_id" label="病房ID" width="120" />
        <el-table-column prop="ward_type" label="病房类型" width="160" />
        <el-table-column prop="start_time" label="值班时间" width="260">
          <template #default="{ row }">
            {{ formatRange(row.start_time, row.end_time) }}
          </template>
        </el-table-column>
        <el-table-column label="负责护士">
          <template #default="{ row }">
            <el-tag v-for="name in row.nurse_names" :key="name" class="tag-gap">{{ name }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200">
          <template #default="{ row }">
            <el-button link type="primary" @click="openEditDialog(row)">编辑</el-button>
            <el-button link type="danger" :loading="deleteLoadingId === row.key" @click="removeSlot(row)">清空</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="editVisible" :title="editFormTitle" width="520px">
      <el-form :model="editForm" label-width="100px">
        <el-form-item label="病房">
          <el-select v-model="editForm.ward_id" placeholder="请选择病房">
            <el-option v-for="ward in context.wards" :key="ward.ward_id" :value="ward.ward_id" :label="ward.ward_type" />
          </el-select>
        </el-form-item>
        <el-form-item label="开始时间">
          <el-date-picker
            v-model="editForm.start_time"
            type="datetime"
            placeholder="请选择开始时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DDTHH:mm:ss"
          />
        </el-form-item>
        <el-form-item label="结束时间">
          <el-date-picker
            v-model="editForm.end_time"
            type="datetime"
            placeholder="请选择结束时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DDTHH:mm:ss"
          />
        </el-form-item>
        <el-form-item label="负责护士">
          <el-select v-model="editForm.nurse_ids" multiple placeholder="请选择护士">
            <el-option
              v-for="nurse in context.nurses"
              :key="nurse.nurse_id"
              :value="nurse.nurse_id"
              :label="formatNurseLabel(nurse)"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editVisible = false">取 消</el-button>
        <el-button type="primary" :loading="editSubmitting" @click="submitEdit">保 存</el-button>
      </template>
    </el-dialog>

    <el-dialog
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
            <small>{{ formatTaskTime(task.time) }} · {{ task.nurse_name }}</small>
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
import { computed, onMounted, reactive, ref, watch } from "vue";
import dayjs from "dayjs";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  fetchHeadScheduleContext,
  upsertWardSchedule,
  autoArrangeSchedules,
  fetchTodayTasks,
  completeTask,
  type HeadScheduleContext,
  type WardScheduleGroup,
  type NurseOption,
  type ScheduleUpsertPayload,
  type AutoSchedulePayload,
  type TodayTaskItem
} from "../../api/modules/nurse";
import { addIgnoredExpiredTaskId, loadIgnoredExpiredTaskIds } from "../../utils/ignoredTasks";

interface TableRow {
  key: string;
  ward_id: number;
  ward_type: string;
  start_time: string;
  end_time: string;
  nurse_ids: number[];
  nurse_names: string[];
}

const context = reactive<HeadScheduleContext>({ wards: [], nurses: [] });
const wardTypeOptions = computed(() => Array.from(new Set(context.wards.map((w) => w.ward_type))));
const loading = ref(false);
const autoLoading = ref(false);
const editVisible = ref(false);
const editSubmitting = ref(false);
const deleteLoadingId = ref<string | null>(null);
const overdueVisible = ref(false);
const overdueLoading = ref(false);
const overdueTasks = ref<TodayTaskItem[]>([]);
const overdueHandleId = ref<number | null>(null);

const autoForm = reactive({
  start_time: dayjs().minute(0).second(0).millisecond(0).format("YYYY-MM-DDTHH:mm:ss"),
  shift_hours: 8,
  shift_count: 3,
  ward_ids: [] as number[],
  ward_types: [] as string[],
  range_mode: "all" as "all" | "type" | "ward"
});

watch(
  () => autoForm.range_mode,
  (mode) => {
    if (mode === "all") {
      autoForm.ward_ids = [];
      autoForm.ward_types = [];
    } else if (mode === "type") {
      autoForm.ward_ids = [];
    } else if (mode === "ward") {
      autoForm.ward_types = [];
    }
  }
);

const editForm = reactive({
  ward_id: null as number | null,
  start_time: "",
  end_time: "",
  nurse_ids: [] as number[],
  source: null as { ward_id: number; start_time: string; end_time: string } | null
});

const editFormTitle = computed(() => (editForm.source ? "编辑排班" : "新增排班"));

const flattenedRows = computed<TableRow[]>(() => {
  const rows: TableRow[] = [];
  context.wards.forEach((ward: WardScheduleGroup) => {
    const groups = new Map<string, TableRow>();
    ward.schedules.forEach((schedule) => {
      const key = `${ward.ward_id}-${schedule.start_time}-${schedule.end_time}`;
      if (!groups.has(key)) {
        groups.set(key, {
          key,
          ward_id: ward.ward_id,
          ward_type: ward.ward_type,
          start_time: schedule.start_time,
          end_time: schedule.end_time,
          nurse_ids: [],
          nurse_names: []
        });
      }
      const group = groups.get(key)!;
      group.nurse_ids.push(schedule.nurse_id);
      group.nurse_names.push(schedule.nurse_name);
    });
    groups.forEach((value) => rows.push(value));
  });
  return rows.sort((a, b) => dayjs(a.start_time).valueOf() - dayjs(b.start_time).valueOf());
});

function formatRange(start: string, end: string) {
  return `${dayjs(start).format("YYYY-MM-DD HH:mm")} ~ ${dayjs(end).format("YYYY-MM-DD HH:mm")}`;
}

function formatNurseLabel(nurse: NurseOption) {
  return nurse.is_head_nurse ? `${nurse.name}（护士长）` : nurse.name;
}

function formatDateTime(value: string) {
  return dayjs(value).format("YYYY-MM-DD HH:mm");
}

function formatStayDuration(hours: number) {
  if (hours < 24) {
    return `${hours.toFixed(1)} 小时`;
  }
  const days = hours / 24;
  return `${days.toFixed(1)} 天`;
}

function formatTaskTime(value: string) {
  return dayjs(value).format("YYYY-MM-DD HH:mm");
}

async function loadOverdueTasks(autoOpen = true) {
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
    ElMessage.error(err.response?.data?.detail ?? "加载过期待办失败");
  } finally {
    overdueLoading.value = false;
  }
}

async function handleOverdue(taskId: number) {
  overdueHandleId.value = taskId;
  try {
    await completeTask(taskId);
    addIgnoredExpiredTaskId(taskId);
    overdueTasks.value = overdueTasks.value.filter((t) => t.task_id !== taskId);
    if (!overdueTasks.value.length) {
      overdueVisible.value = false;
    }
    ElMessage.success("已处理该过期待办");
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail ?? "处理失败");
  } finally {
    overdueHandleId.value = null;
  }
}

async function loadContext() {
  loading.value = true;
  try {
    const { data } = await fetchHeadScheduleContext();
    context.wards = data.wards;
    context.nurses = data.nurses;
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail ?? "加载排班数据失败");
  } finally {
    loading.value = false;
  }
}

function initEditFormDefaults() {
  editForm.ward_id = context.wards[0]?.ward_id ?? null;
  const start = dayjs().minute(0).second(0).millisecond(0);
  editForm.start_time = start.format("YYYY-MM-DDTHH:mm:ss");
  editForm.end_time = start.add(8, "hour").format("YYYY-MM-DDTHH:mm:ss");
  editForm.nurse_ids = [];
  editForm.source = null;
}

function openCreateDialog() {
  initEditFormDefaults();
  editVisible.value = true;
}

function openEditDialog(row: TableRow) {
  editForm.ward_id = row.ward_id;
  editForm.start_time = row.start_time;
  editForm.end_time = row.end_time;
  editForm.nurse_ids = [...row.nurse_ids];
  editForm.source = { ward_id: row.ward_id, start_time: row.start_time, end_time: row.end_time };
  editVisible.value = true;
}

async function submitEdit() {
  if (!editForm.ward_id || !editForm.start_time || !editForm.end_time) {
    ElMessage.warning("请完善病房与时间段");
    return;
  }
  if (dayjs(editForm.end_time).valueOf() <= dayjs(editForm.start_time).valueOf()) {
    ElMessage.warning("结束时间需晚于开始时间");
    return;
  }
  const payload: ScheduleUpsertPayload = {
    ward_id: editForm.ward_id,
    start_time: editForm.start_time,
    end_time: editForm.end_time,
    nurse_ids: [...editForm.nurse_ids]
  };
  if (editForm.source) {
    payload.source_ward_id = editForm.source.ward_id;
    payload.source_start_time = editForm.source.start_time;
    payload.source_end_time = editForm.source.end_time;
  }
  editSubmitting.value = true;
  try {
    await upsertWardSchedule(payload);
    ElMessage.success("排班已保存");
    editVisible.value = false;
    await loadContext();
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail ?? "保存失败");
  } finally {
    editSubmitting.value = false;
  }
}

async function removeSlot(row: TableRow) {
  try {
    await ElMessageBox.confirm("确认清空该时间段的所有护士吗？", "提示", { confirmButtonText: "确定", cancelButtonText: "取消", type: "warning" });
  } catch {
    return;
  }
  deleteLoadingId.value = row.key;
  try {
    await upsertWardSchedule({
      ward_id: row.ward_id,
      start_time: row.start_time,
      end_time: row.end_time,
      nurse_ids: [],
      source_ward_id: row.ward_id,
      source_start_time: row.start_time,
      source_end_time: row.end_time
    });
    ElMessage.success("已清空该排班");
    await loadContext();
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail ?? "操作失败");
  } finally {
    deleteLoadingId.value = null;
  }
}

async function handleAutoSchedule() {
  if (!autoForm.start_time) {
    ElMessage.warning("请选择开始时间");
    return;
  }
  let selectedWardIds: number[] | null = null;
  if (autoForm.range_mode === "type") {
    const matched = context.wards
      .filter((w) => autoForm.ward_types.includes(w.ward_type))
      .map((w) => w.ward_id);
    if (!matched.length) {
      ElMessage.warning("请选择至少一个病房类型");
      return;
    }
    selectedWardIds = matched;
  } else if (autoForm.range_mode === "ward") {
    if (!autoForm.ward_ids.length) {
      ElMessage.warning("请选择至少一个病房");
      return;
    }
    selectedWardIds = [...autoForm.ward_ids];
  }
  const payload: AutoSchedulePayload = {
    start_time: autoForm.start_time,
    shift_hours: autoForm.shift_hours,
    shift_count: autoForm.shift_count
  };
  if (selectedWardIds && selectedWardIds.length) {
    payload.ward_ids = selectedWardIds;
  }
  autoLoading.value = true;
  try {
    const { data } = await autoArrangeSchedules(payload);
    ElMessage.success(data.detail ?? "排班已生成");
    await loadContext();
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail ?? "排班失败");
  } finally {
    autoLoading.value = false;
  }
}

onMounted(() => {
  loadContext();
});
</script>

<style scoped>
.head-nurse-page {
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

.card-header small {
  color: #94a3b8;
}

.auto-form {
  display: flex;
  flex-wrap: wrap;
  gap: 12px 24px;
}

.auto-form .wide-item {
  flex: 1 1 100%;
}

.ward-select {
  width: 100%;
}

.ward-range {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.auto-form .unit {
  margin-left: 6px;
  color: #94a3b8;
}

.tag-gap {
  margin-right: 6px;
  margin-bottom: 4px;
}

.auto-card {
  border-left: 3px solid var(--el-color-primary);
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
