<template>
  <div class="admin-logs">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>操作日志</span>
          <small>可查看登录与操作轨迹，支持按账号/角色/路径筛选</small>
        </div>
      </template>
      <div class="filter-bar">
        <el-input
          v-model="filters.user_phone"
          placeholder="手机号"
          maxlength="11"
          clearable
          style="width: 160px"
        />
        <el-select v-model="filters.role" placeholder="全部角色" clearable style="width: 140px">
          <el-option
            v-for="item in roleOptions"
            :key="item.value"
            :label="item.label"
            :value="item.value"
          />
        </el-select>
        <el-input
          v-model="filters.path_prefix"
          placeholder="按路径前缀筛选，如 /api"
          clearable
          style="width: 240px"
        />
        <el-select v-model="filters.limit" placeholder="数量" style="width: 120px">
          <el-option v-for="n in limitOptions" :key="n" :label="`最新 ${n} 条`" :value="n" />
        </el-select>
        <el-button type="primary" :loading="loading" @click="loadLogs">查询</el-button>
      </div>
      <el-table :data="logs" v-loading="loading" border size="small">
        <el-table-column prop="created_at" label="时间" width="180">
          <template #default="scope">
            {{ formatDate(scope.row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="user_phone" label="手机号" width="140" />
        <el-table-column prop="role" label="角色" width="100">
          <template #default="scope">
            {{ displayRole(scope.row.role) }}
          </template>
        </el-table-column>
        <el-table-column prop="method" label="方法" width="90" />
        <el-table-column prop="status_code" label="状态" width="90" />
        <el-table-column prop="path" label="路径" min-width="180" show-overflow-tooltip />
        <el-table-column prop="action" label="动作" min-width="160" show-overflow-tooltip />
        <el-table-column prop="ip_address" label="IP" width="140" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import dayjs from "dayjs";
import { fetchActionLogs, type UserActionLogItem } from "../../api/modules/admin";

const loading = ref(false);
const logs = ref<UserActionLogItem[]>([]);

const roleOptions = [
  { label: "院长", value: "管理员" },
  { label: "医生", value: "医生" },
  { label: "护士", value: "护士" },
  { label: "药师", value: "药师" },
  { label: "患者", value: "患者" }
];
const limitOptions = [50, 100, 200, 500];

const filters = reactive({
  user_phone: "",
  role: "" as string | undefined,
  path_prefix: "",
  limit: 200
});

function formatDate(value?: string) {
  if (!value) return "-";
  return dayjs(value).format("YYYY-MM-DD HH:mm:ss");
}

async function loadLogs() {
  loading.value = true;
  try {
    const params: Record<string, any> = {};
    if (filters.user_phone) params.user_phone = filters.user_phone;
    if (filters.role) params.role = filters.role;
    if (filters.path_prefix) params.path_prefix = filters.path_prefix;
    if (filters.limit) params.limit = filters.limit;
    const { data } = await fetchActionLogs(params);
    logs.value = data ?? [];
  } catch (err: any) {
    console.error(err);
    ElMessage.error(err?.response?.data?.detail || "获取日志失败");
  } finally {
    loading.value = false;
  }
}

function displayRole(role: string | undefined) {
  if (!role) return "-";
  return role === "管理员" ? "院长" : role;
}

onMounted(() => {
  void loadLogs();
});
</script>

<style scoped>
.admin-logs {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.card-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-header small {
  color: #6b7280;
}

.filter-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}
</style>
