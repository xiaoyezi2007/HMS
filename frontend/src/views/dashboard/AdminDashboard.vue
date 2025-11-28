<template>
  <div class="admin-board">
    <el-alert
      title="院长可在此创建与注销医生/护士/药师账户，初始密码统一为 123456，首次登录后请提醒及时修改"
      type="info"
      show-icon
    />

    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>新增医护账号</span>
          <small>手机号将作为登录名，初始密码固定为 123456</small>
        </div>
      </template>
      <el-form :model="createForm" label-width="100px">
        <el-form-item label="手机号">
          <el-input v-model="createForm.phone" maxlength="11" placeholder="请输入 11 位手机号" />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="createForm.username" maxlength="20" placeholder="展示用昵称" />
        </el-form-item>
        <el-form-item label="角色">
          <el-select v-model="createForm.role">
            <el-option v-for="role in roleOptions" :key="role.value" :label="role.label" :value="role.value" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isNurseRole" label="护士姓名">
          <el-input v-model="createForm.nurse_name" maxlength="20" placeholder="请输入真实姓名" />
        </el-form-item>
        <el-form-item v-if="isNurseRole" label="性别">
          <el-radio-group v-model="createForm.nurse_gender">
            <el-radio-button v-for="item in genderOptions" :key="item.value" :label="item.value">
              {{ item.label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="isDoctorRole" label="医生姓名">
          <el-input v-model="createForm.doctor_name" maxlength="20" placeholder="请输入真实姓名" />
        </el-form-item>
        <el-form-item v-if="isDoctorRole" label="性别">
          <el-radio-group v-model="createForm.doctor_gender">
            <el-radio-button v-for="item in genderOptions" :key="item.value" :label="item.value">
              {{ item.label }}
            </el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item v-if="isDoctorRole" label="医生职称">
          <el-select v-model="createForm.doctor_title" placeholder="请选择职称">
            <el-option v-for="option in doctorTitleOptions" :key="option" :label="option" :value="option" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="isDoctorRole" label="所属科室">
          <el-select
            v-model="createForm.dept_id"
            placeholder="请选择科室"
            filterable
            :loading="deptLoading"
          >
            <el-option
              v-for="dept in departments"
              :key="dept.dept_id"
              :label="dept.dept_name"
              :value="dept.dept_id"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            :loading="creating"
            :disabled="submitDisabled"
            @click="handleCreate"
          >
            创建账号
          </el-button>
          <el-button @click="resetForm">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>医护账号管理</span>
          <small>统一查看现有账号，并在表格中完成职称与护士长设置</small>
        </div>
      </template>
      <div class="management-toolbar">
        <el-select v-model="filterRole" placeholder="全部角色" clearable @change="handleFilterChange">
          <el-option label="全部角色" value="" />
          <el-option v-for="role in roleOptions" :key="role.value" :label="role.label" :value="role.value" />
        </el-select>
        <el-input v-model="searchName" placeholder="按姓名/昵称查询" clearable />
        <el-input v-model="searchPhone" placeholder="按手机号查询" clearable maxlength="11" />
        <el-button type="primary" link :loading="tableLoading" @click="refreshStaffData">刷新</el-button>
      </div>
      <el-table :data="pagedRows" v-loading="tableLoading" style="width: 100%">
        <el-table-column prop="displayName" label="姓名" min-width="140" />
        <el-table-column prop="phone" label="手机号" min-width="140" />
        <el-table-column prop="role" label="角色" min-width="120" />
        <el-table-column label="所属科室" min-width="120">
          <template #default="scope">
            {{ scope.row.doctorProfile?.dept_name || "-" }}
          </template>
        </el-table-column>
        <el-table-column label="状态" min-width="100">
          <template #default="scope">
            {{ scope.row.status || "-" }}
          </template>
        </el-table-column>
        <el-table-column label="注册时间" min-width="180">
          <template #default="scope">
            {{ scope.row.register_time ? formatDate(scope.row.register_time) : "-" }}
          </template>
        </el-table-column>
        <el-table-column label="医生职称" min-width="200">
          <template #default="scope">
            <el-select
              v-if="scope.row.doctorProfile"
              v-model="scope.row.doctorProfile.title"
              size="small"
              @change="(value) => handleDoctorTitleSelect(scope.row.doctorProfile?.doctor_id, value)"
            >
              <el-option
                v-for="option in doctorTitleOptions"
                :key="option"
                :label="option"
                :value="option"
              />
            </el-select>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="护士长" min-width="140">
          <template #default="scope">
            <el-switch
              v-if="scope.row.nurseProfile"
              :model-value="scope.row.nurseProfile.is_head_nurse"
              inline-prompt
              active-text="是"
              inactive-text="否"
              :loading="nurseLoading"
              @change="(value) =>
                handleNurseHeadToggle(scope.row.nurseProfile?.nurse_id, value)
              "
            />
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="140">
          <template #default="scope">
            <el-button
              type="danger"
              link
              :disabled="!scope.row.hasAccount"
              @click="handleDelete(scope.row.phone)"
            >删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <div class="management-pagination">
        <el-pagination
          background
          layout="total, sizes, prev, pager, next"
          :current-page="currentPage"
          :page-size="pageSize"
          :page-sizes="pageSizeOptions"
          :total="filteredRows.length"
          @size-change="handlePageSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  createStaffAccount,
  deleteStaffAccount,
  fetchStaffAccounts,
  fetchDoctors,
  updateDoctorTitle,
  fetchNurses,
  updateNurseHeadStatus,
  fetchDepartments,
  type DepartmentItem
} from "../../api/modules/admin";
import type { StaffAccount, DoctorProfile, NurseProfile } from "../../api/modules/admin";

interface RoleOption {
  label: string;
  value: string;
}

const roleOptions: RoleOption[] = [
  { label: "医生", value: "医生" },
  { label: "护士", value: "护士" },
  { label: "药师", value: "药师" }
];

const doctorTitleOptions = ["普通医师", "主治医师"];
const genderOptions = [
  { label: "男", value: "男" },
  { label: "女", value: "女" }
];

const createForm = reactive({
  phone: "",
  username: "",
  role: roleOptions.length ? roleOptions[0].value : "医生",
  dept_id: null as number | null,
  doctor_name: "",
  doctor_gender: "",
  doctor_title: doctorTitleOptions[0],
  nurse_name: "",
  nurse_gender: ""
});

const creating = ref(false);
const listLoading = ref(false);
const accountList = ref<StaffAccount[]>([]);
const filterRole = ref<string>("");
const doctorList = ref<DoctorProfile[]>([]);
const doctorLoading = ref(false);
const nurseList = ref<NurseProfile[]>([]);
const nurseLoading = ref(false);
const searchName = ref("");
const searchPhone = ref("");
const currentPage = ref(1);
const pageSize = ref(10);
const pageSizeOptions = [5, 10, 20, 50];
const departments = ref<DepartmentItem[]>([]);
const deptLoading = ref(false);
const isDoctorRole = computed(() => createForm.role === "医生");
const isNurseRole = computed(() => createForm.role === "护士");
const doctorFormInvalid = computed(() => {
  if (!isDoctorRole.value) {
    return false;
  }
  return (
    !createForm.dept_id ||
    !createForm.doctor_name.trim() ||
    !createForm.doctor_gender ||
    !createForm.doctor_title
  );
});
const nurseFormInvalid = computed(() => {
  if (!isNurseRole.value) {
    return false;
  }
  return !createForm.nurse_name.trim() || !createForm.nurse_gender;
});
const submitDisabled = computed(() => {
  if (isDoctorRole.value) {
    return doctorFormInvalid.value;
  }
  if (isNurseRole.value) {
    return nurseFormInvalid.value;
  }
  return false;
});

type ManagementRow = {
  phone: string;
  displayName: string;
  role: string;
  status?: string;
  register_time?: string;
  hasAccount: boolean;
  doctorProfile?: DoctorProfile;
  nurseProfile?: NurseProfile;
};

const doctorMap = computed<Record<string, DoctorProfile>>(() => {
  return doctorList.value.reduce((acc, doctor) => {
    acc[doctor.phone] = doctor;
    return acc;
  }, {} as Record<string, DoctorProfile>);
});

const nurseMap = computed<Record<string, NurseProfile>>(() => {
  return nurseList.value.reduce((acc, nurse) => {
    acc[nurse.phone] = nurse;
    return acc;
  }, {} as Record<string, NurseProfile>);
});

const accountPhoneSet = computed(() => new Set(accountList.value.map((item) => item.phone)));

const doctorOnlyRows = computed<ManagementRow[]>(() => {
  return doctorList.value
    .filter((doctor) => !accountPhoneSet.value.has(doctor.phone))
    .map((doctor) => ({
      phone: doctor.phone,
      displayName: doctor.name,
      role: "医生",
      hasAccount: false,
      doctorProfile: doctor
    }));
});

const nurseOnlyRows = computed<ManagementRow[]>(() => {
  return nurseList.value
    .filter((nurse) => !accountPhoneSet.value.has(nurse.phone))
    .map((nurse) => ({
      phone: nurse.phone,
      displayName: nurse.name,
      role: "护士",
      hasAccount: false,
      nurseProfile: nurse
    }));
});

const managementRows = computed<ManagementRow[]>(() => {
  const accountRows = accountList.value.map((account) => {
    const doctorProfile = doctorMap.value[account.phone];
    const nurseProfile = nurseMap.value[account.phone];
    const displayName = doctorProfile?.name || nurseProfile?.name || account.username;
    return {
      phone: account.phone,
      displayName,
      role: account.role,
      status: account.status,
      register_time: account.register_time,
      hasAccount: true,
      doctorProfile,
      nurseProfile
    };
  });
  return [...accountRows, ...doctorOnlyRows.value, ...nurseOnlyRows.value];
});

const filteredRows = computed<ManagementRow[]>(() => {
  const phoneKeyword = searchPhone.value.trim();
  const nameKeyword = searchName.value.trim().toLowerCase();
  return managementRows.value.filter((row) => {
    const matchesRole = filterRole.value ? row.role === filterRole.value : true;
    const matchesPhone = phoneKeyword ? row.phone.includes(phoneKeyword) : true;
    const displayName = row.displayName.toLowerCase();
    const matchesName = nameKeyword ? displayName.includes(nameKeyword) : true;
    return matchesRole && matchesPhone && matchesName;
  });
});

const pagedRows = computed<ManagementRow[]>(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return filteredRows.value.slice(start, end);
});

const tableLoading = computed(() => listLoading.value || doctorLoading.value || nurseLoading.value);

watch([filterRole, searchName, searchPhone], () => {
  currentPage.value = 1;
});

function resetForm() {
  createForm.phone = "";
  createForm.username = "";
  createForm.role = roleOptions.length ? roleOptions[0].value : "医生";
  createForm.dept_id = null;
  createForm.doctor_name = "";
  createForm.doctor_gender = "";
  createForm.doctor_title = doctorTitleOptions[0];
  createForm.nurse_name = "";
  createForm.nurse_gender = "";
}

function formatDate(value: string) {
  if (!value) {
    return "-";
  }
  return value.replace("T", " ").slice(0, 19);
}

function isValidPhone(phone: string) {
  return /^1\d{10}$/.test(phone);
}

function loadAccounts() {
  listLoading.value = true;
  const roleParam = filterRole.value ? filterRole.value : undefined;
  return fetchStaffAccounts(roleParam)
    .then(({ data }) => {
      accountList.value = data;
    })
    .catch((error: any) => {
      const message = error && error.response && error.response.data && error.response.data.detail;
      ElMessage.error(message || "账号列表加载失败");
    })
    .then(() => {
      listLoading.value = false;
    });
}

function handleCreate() {
  if (!createForm.phone || !createForm.username) {
    ElMessage.warning("请填写完整信息");
    return;
  }
  if (!isValidPhone(createForm.phone)) {
    ElMessage.warning("请输入合法的 11 位手机号");
    return;
  }
  if (isDoctorRole.value) {
    if (!createForm.doctor_name.trim()) {
      ElMessage.warning("请输入医生姓名");
      return;
    }
    if (!createForm.doctor_gender) {
      ElMessage.warning("请选择医生性别");
      return;
    }
    if (!createForm.doctor_title) {
      ElMessage.warning("请选择医生职称");
      return;
    }
    if (!createForm.dept_id) {
      ElMessage.warning("请选择医生所属科室");
      return;
    }
  }
  if (isNurseRole.value) {
    if (!createForm.nurse_name.trim()) {
      ElMessage.warning("请输入护士姓名");
      return;
    }
    if (!createForm.nurse_gender) {
      ElMessage.warning("请选择护士性别");
      return;
    }
  }
  creating.value = true;
  const payload = {
    phone: createForm.phone,
    username: createForm.username,
    role: createForm.role,
    dept_id: isDoctorRole.value ? createForm.dept_id ?? undefined : undefined,
    doctor_name: isDoctorRole.value ? createForm.doctor_name : undefined,
    doctor_gender: isDoctorRole.value ? createForm.doctor_gender : undefined,
    doctor_title: isDoctorRole.value ? createForm.doctor_title : undefined,
    nurse_name: isNurseRole.value ? createForm.nurse_name : undefined,
    nurse_gender: isNurseRole.value ? createForm.nurse_gender : undefined
  };
  createStaffAccount(payload)
    .then(() => {
      ElMessage.success("账号创建成功（初始密码 123456）");
      resetForm();
      return loadAccounts();
    })
    .catch((error: any) => {
      const message = error && error.response && error.response.data && error.response.data.detail;
      ElMessage.error(message || "创建失败");
    })
    .then(() => {
      creating.value = false;
    });
}

function handleDelete(phone: string) {
  ElMessageBox.confirm("确定要删除账号 " + phone + " 吗？", "提示", { type: "warning" })
    .then(() => {
      return deleteStaffAccount(phone)
        .then(() => {
          ElMessage.success("删除成功");
          return loadAccounts();
        })
        .catch((error: any) => {
          const message = error && error.response && error.response.data && error.response.data.detail;
          ElMessage.error(message || "删除失败");
        });
    })
    .catch(() => {
      /* 用户取消 */
    });
}

function handleFilterChange() {
  currentPage.value = 1;
}

function handlePageSizeChange(size: number) {
  pageSize.value = size;
  currentPage.value = 1;
}

function handlePageChange(page: number) {
  currentPage.value = page;
}

function loadDoctors() {
  doctorLoading.value = true;
  return fetchDoctors()
    .then(({ data }) => {
      doctorList.value = data;
    })
    .catch((error: any) => {
      const message = error && error.response && error.response.data && error.response.data.detail;
      ElMessage.error(message || "医生列表加载失败");
    })
    .then(() => {
      doctorLoading.value = false;
    });
}

function handleDoctorTitleSelect(doctorId: number | undefined, titleValue: unknown) {
  if (!doctorId) {
    return;
  }
  const nextTitle = typeof titleValue === "string" ? titleValue : "主治医师";
  updateDoctorTitle(doctorId, nextTitle)
    .then(() => {
      ElMessage.success("职称已更新");
      return loadDoctors();
    })
    .catch((error: any) => {
      const message = error && error.response && error.response.data && error.response.data.detail;
      ElMessage.error(message || "更新失败");
      return loadDoctors();
    });
}

function loadNurses() {
  nurseLoading.value = true;
  return fetchNurses()
    .then(({ data }) => {
      nurseList.value = data;
    })
    .catch((error: any) => {
      const message = error && error.response && error.response.data && error.response.data.detail;
      ElMessage.error(message || "护士列表加载失败");
    })
    .then(() => {
      nurseLoading.value = false;
    });
}

function handleNurseHeadToggle(nurseId: number | undefined, isHead: boolean) {
  if (!nurseId) {
    return;
  }
  updateNurseHeadStatus(nurseId, isHead)
    .then(() => {
      ElMessage.success(isHead ? "已设为护士长" : "已取消护士长");
      return loadNurses();
    })
    .catch((error: any) => {
      const message = error && error.response && error.response.data && error.response.data.detail;
      ElMessage.error(message || "操作失败");
      return loadNurses();
    });
}

onMounted(() => {
  refreshStaffData();
  loadDepartments();
});

function refreshStaffData() {
  loadAccounts();
  loadDoctors();
  loadNurses();
}

async function loadDepartments() {
  try {
    deptLoading.value = true;
    const { data } = await fetchDepartments();
    departments.value = data;
  } catch (error: any) {
    const message = error && error.response && error.response.data && error.response.data.detail;
    ElMessage.error(message || "科室数据获取失败");
  } finally {
    deptLoading.value = false;
  }
}

watch(
  () => createForm.role,
  (role) => {
    if (role !== "医生") {
      createForm.dept_id = null;
      createForm.doctor_name = "";
      createForm.doctor_gender = "";
      createForm.doctor_title = doctorTitleOptions[0];
    }
    if (role !== "护士") {
      createForm.nurse_name = "";
      createForm.nurse_gender = "";
    }
  }
);
</script>

<style scoped>
.admin-board {
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
  color: #94a3b8;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.management-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}

.management-toolbar .el-select,
.management-toolbar .el-input {
  flex: 1 1 200px;
}

.management-pagination {
  margin-top: 16px;
  display: flex;
  justify-content: flex-end;
}
</style>
