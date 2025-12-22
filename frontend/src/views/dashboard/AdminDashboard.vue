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
          <span>新增科室</span>
          <small>仅院长可操作，科室名称需唯一</small>
        </div>
      </template>
      <el-form :model="deptForm" label-width="90px">
        <el-row :gutter="12">
          <el-col :xs="24" :sm="14" :md="10">
            <el-form-item label="科室名称">
              <el-input v-model="deptForm.dept_name" placeholder="如 心内科" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="10" :md="8">
            <el-form-item label="电话">
              <el-input v-model="deptForm.telephone" placeholder="可选" />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="24" :md="6" class="form-actions">
            <el-button type="primary" :loading="deptCreating" @click="handleCreateDepartment">新增科室</el-button>
            <el-button @click="resetDeptForm">重置</el-button>
          </el-col>
        </el-row>
      </el-form>
    </el-card>

    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>病房管理</span>
          <small>房间号需手工录入（101-999），科室与病房类型决定床位数</small>
        </div>
      </template>
      <el-form :model="wardForm" label-width="90px">
        <el-row :gutter="12">
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="房间号">
              <el-input-number
                v-model="wardForm.ward_id"
                :controls="false"
                placeholder="101-999"
                style="width: 100%"
              />
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="8">
            <el-form-item label="科室">
              <el-select v-model="wardForm.dept_id" placeholder="选择所属科室" filterable :loading="deptLoading">
                <el-option v-for="dept in departments" :key="dept.dept_id" :label="dept.dept_name" :value="dept.dept_id" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="12" :md="6">
            <el-form-item label="类型">
              <el-select v-model="wardForm.type" placeholder="选择病房类型">
                <el-option
                  v-for="option in availableWardTypeOptions"
                  :key="option.value"
                  :label="`${option.label} · ${option.bedCount} 床`"
                  :value="option.value"
                />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :xs="24" :sm="24" :md="4" class="form-actions">
            <el-button type="primary" :loading="wardCreating" @click="handleCreateWard">新增病房</el-button>
            <el-button @click="resetWardForm">重置</el-button>
          </el-col>
        </el-row>
      </el-form>
      <div class="management-toolbar" style="margin-top: 12px">
        <el-select
          v-model="searchWardDept"
          placeholder="选择科室筛选"
          clearable
          filterable
          style="min-width: 180px"
        >
          <el-option v-for="dept in departments" :key="dept.dept_id" :label="dept.dept_name" :value="dept.dept_name" />
        </el-select>
        <el-select
          v-model="searchWardType"
          placeholder="选择病房类型"
          clearable
          style="min-width: 180px"
        >
          <el-option v-for="opt in wardTypeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
        </el-select>
        <el-button type="primary" link :loading="wardLoading" @click="loadWards">刷新</el-button>
      </div>
      <el-table :data="visibleWards" v-loading="wardLoading" size="small" border>
        <el-table-column prop="ward_id" label="房间号" width="100" />
        <el-table-column prop="dept_name" label="科室" min-width="160" />
        <el-table-column prop="type" label="病房类型" min-width="140" />
        <el-table-column prop="bed_count" label="床位数" width="120" />
        <el-table-column label="操作" width="120">
          <template #default="scope">
            <el-button type="danger" link @click="handleHideWard(scope.row.ward_id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

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
        <el-form-item v-if="isDoctorRole" label="医生级别">
          <el-select v-model="createForm.doctor_title" placeholder="请选择医生级别">
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
          <span>批量导入医护账号</span>
          <small>下载模板后批量编辑，再上传 Excel/CSV 一键创建账号</small>
        </div>
      </template>
      <div class="import-card">
        <div class="import-instructions">
          <p>· 保留表头不变，手机号、用户名、角色为必填，医生需在“所属科室 ID”列填入数字，可参考模板中的“科室列表”，并补充姓名/性别/级别。</p>
          <p>· 支持 .xlsx / .csv 文件。模板已包含示例，重复手机号会自动跳过。</p>
        </div>
        <div class="import-actions">
          <el-button type="primary" plain :loading="templateLoading" @click="handleDownloadTemplate">
            下载模板
          </el-button>
          <el-upload
            ref="uploadRef"
            class="upload-area"
            drag
            :auto-upload="false"
            :file-list="uploadFiles"
            accept=".xlsx,.csv"
            @change="handleImportFileChange"
            @remove="handleImportFileRemove"
          >
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="el-upload__text">
              将文件拖拽到此或<em>点击上传</em>
            </div>
            <template #tip>
              <div class="upload-tip">建议直接在模板上编辑，单文件不超过 5MB</div>
            </template>
          </el-upload>
          <el-button type="success" :loading="importing" @click="handleImportSubmit">
            执行导入
          </el-button>
        </div>
      </div>
      <el-alert
        v-if="importSummary"
        type="info"
        show-icon
        :closable="false"
        class="import-summary"
        :title="`共处理 ${importSummary.total_rows} 行，成功 ${importSummary.success_count} 条，失败 ${importSummary.errors.length} 条`"
      />
      <el-table
        v-if="importSummary?.errors?.length"
        :data="importSummary.errors"
        size="small"
        border
        class="import-error-table"
        empty-text="全部导入成功"
      >
        <el-table-column prop="row_number" label="行号" width="100" />
        <el-table-column prop="message" label="失败原因" />
      </el-table>
    </el-card>

    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <span>医护账号管理</span>
          <small>统一查看现有账号，并在表格中完成医生级别与护士长设置</small>
        </div>
      </template>
      <div class="management-toolbar">
        <el-select v-model="filterRole" placeholder="全部角色" clearable @change="handleFilterChange">
          <el-option label="全部角色" value="" />
          <el-option v-for="role in roleOptions" :key="role.value" :label="role.label" :value="role.value" />
        </el-select>
        <el-input v-model="searchName" placeholder="按姓名/昵称查询" clearable />
        <el-input v-model="searchPhone" placeholder="按手机号查询" clearable maxlength="11" />
        <el-checkbox v-model="onlyActive">仅查看在职员工</el-checkbox>
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
        <el-table-column label="医生级别" min-width="200">
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
import { UploadFilled } from "@element-plus/icons-vue";
import type { UploadInstance, UploadProps, UploadUserFile } from "element-plus";
import {
  createStaffAccount,
  deleteStaffAccount,
  fetchStaffAccounts,
  fetchDoctors,
  updateDoctorTitle,
  fetchNurses,
  updateNurseHeadStatus,
  fetchDepartments,
  fetchAdminWards,
  createDepartment,
  createWard,
  downloadAccountTemplate,
  importStaffAccounts,
  type DepartmentItem,
  type WardItem,
  type AccountImportResult
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

const doctorTitleOptions = ["普通医师", "专家医师"];
const genderOptions = [
  { label: "男", value: "男" },
  { label: "女", value: "女" }
];

const ICU_TYPE_VALUE = "重症监护";
const wardTypeOptions = [
  { label: "单人房", value: "单人房", bedCount: 1 },
  { label: "双人房", value: "双人房", bedCount: 2 },
  { label: "四人病房", value: "四人病房", bedCount: 4 },
  { label: "重症监护", value: ICU_TYPE_VALUE, bedCount: 1 }
];

const uploadRef = ref<UploadInstance>();
const uploadFiles = ref<UploadUserFile[]>([]);
const importFile = ref<File | null>(null);
const importing = ref(false);
const templateLoading = ref(false);
const importSummary = ref<AccountImportResult | null>(null);
const allowedImportExts = [".xlsx", ".csv"];
const maxImportSizeBytes = 5 * 1024 * 1024;

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
const onlyActive = ref(true);
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
const deptCreating = ref(false);
const wardCreating = ref(false);
const wardLoading = ref(false);
const wardList = ref<WardItem[]>([]);
const hiddenWardIds = ref<Set<number>>(new Set());
const searchWardDept = ref("");
const searchWardType = ref("");
const visibleWards = computed(() => {
  return wardList.value.filter((w) => {
    const matchDept = searchWardDept.value
      ? w.dept_name.toLowerCase() === searchWardDept.value.toLowerCase()
      : true;
    const matchType = searchWardType.value
      ? w.type === searchWardType.value
      : true;
    const isHidden = hiddenWardIds.value.has(w.ward_id);
    return matchDept && matchType && !isHidden;
  });
});
const deptForm = reactive({
  dept_name: "",
  telephone: ""
});
const defaultWardType = wardTypeOptions.find((item) => item.value !== ICU_TYPE_VALUE) ?? wardTypeOptions[0];
const wardForm = reactive({
  ward_id: null as number | null,
  dept_id: null as number | null,
  type: defaultWardType?.value ?? "",
  bed_count: defaultWardType?.bedCount ?? 0
});
const selectedWardDept = computed(() =>
  departments.value.find((dept) => dept.dept_id === wardForm.dept_id)
);
const availableWardTypeOptions = computed(() => wardTypeOptions);
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
    const matchesActive = onlyActive.value
      ? !row.status || row.status === "启用" || row.status === "active"
      : true;
    return matchesRole && matchesPhone && matchesName && matchesActive;
  });
});

const pagedRows = computed<ManagementRow[]>(() => {
  const start = (currentPage.value - 1) * pageSize.value;
  const end = start + pageSize.value;
  return filteredRows.value.slice(start, end);
});

const tableLoading = computed(() => listLoading.value || doctorLoading.value || nurseLoading.value);

watch([filterRole, searchName, searchPhone, onlyActive], () => {
  currentPage.value = 1;
});

watch(
  () => wardForm.type,
  (nextType) => {
    const matched = wardTypeOptions.find((item) => item.value === nextType);
    wardForm.bed_count = matched?.bedCount ?? 0;
  }
);

watch(
  () => wardForm.dept_id,
  () => {
    const options = availableWardTypeOptions.value;
    if (!options.length) {
      wardForm.type = "";
      wardForm.bed_count = 0;
      return;
    }
    if (!options.some((item) => item.value === wardForm.type)) {
      wardForm.type = options[0].value;
    }
  }
);

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

function resetDeptForm() {
  deptForm.dept_name = "";
  deptForm.telephone = "";
}

function resetWardForm() {
  wardForm.ward_id = null;
  wardForm.dept_id = null;
  wardForm.type = defaultWardType?.value ?? "";
  wardForm.bed_count = defaultWardType?.bedCount ?? 0;
}

function clearImportSelection() {
  uploadRef.value?.clearFiles();
  uploadFiles.value = [];
  importFile.value = null;
}

const handleImportFileChange: UploadProps["onChange"] = (file, fileList) => {
  importSummary.value = null;
  const rawFile = file?.raw ?? null;
  if (!rawFile) {
    importFile.value = null;
    uploadFiles.value = [];
    return;
  }
  const fileName = (file.name || "").toLowerCase();
  const isAllowed = allowedImportExts.some((ext) => fileName.endsWith(ext));
  if (!isAllowed) {
    ElMessage.warning("仅支持 .xlsx 或 .csv 文件");
    clearImportSelection();
    return;
  }
  if (rawFile.size > maxImportSizeBytes) {
    ElMessage.warning("文件大小请控制在 5MB 以内");
    clearImportSelection();
    return;
  }
  importFile.value = rawFile;
  uploadFiles.value = fileList.slice(-1);
};

const handleImportFileRemove: UploadProps["onRemove"] = () => {
  importFile.value = null;
  uploadFiles.value = [];
};

async function handleDownloadTemplate() {
  try {
    templateLoading.value = true;
    const response = await downloadAccountTemplate();
    const blob = response.data;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    const stamp = new Date().toISOString().slice(0, 10).replace(/-/g, "");
    link.href = url;
    link.download = `staff-account-template-${stamp}.xlsx`;
    link.click();
    URL.revokeObjectURL(url);
  } catch (error: any) {
    const message = error?.response?.data?.detail;
    ElMessage.error(message || "模板下载失败");
  } finally {
    templateLoading.value = false;
  }
}

async function handleImportSubmit() {
  if (!importFile.value) {
    ElMessage.warning("请先选择要导入的模板文件");
    return;
  }
  importing.value = true;
  importSummary.value = null;
  const formData = new FormData();
  formData.append("file", importFile.value);
  try {
    const { data } = await importStaffAccounts(formData);
    importSummary.value = data;
    if (data.success_count > 0) {
      ElMessage.success(`成功导入 ${data.success_count} 个账号`);
      refreshStaffData();
      clearImportSelection();
    }
    if (data.errors.length) {
      ElMessage.warning(`有 ${data.errors.length} 行导入失败，请查看下方列表`);
    }
  } catch (error: any) {
    const message = error?.response?.data?.detail;
    ElMessage.error(message || "导入失败");
  } finally {
    importing.value = false;
  }
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
      ElMessage.warning("请选择医生级别");
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

function normalizeDoctorLevel(value: string | null | undefined) {
  if (!value) return "";
  return value === "主治医师" ? "专家医师" : value;
}

function handleCreateDepartment() {
  if (!deptForm.dept_name.trim()) {
    ElMessage.warning("请填写科室名称");
    return;
  }
  deptCreating.value = true;
  createDepartment({
    dept_name: deptForm.dept_name.trim(),
    telephone: deptForm.telephone.trim() || undefined
  })
    .then(() => {
      ElMessage.success("新增科室成功");
      resetDeptForm();
      return loadDepartments();
    })
    .catch((error: any) => {
      const message = error?.response?.data?.detail;
      ElMessage.error(message || "新增科室失败");
    })
    .then(
      () => {
        deptCreating.value = false;
      },
      () => {
        deptCreating.value = false;
      }
    );
}

function handleCreateWard() {
  if (!wardForm.dept_id) {
    ElMessage.warning("请选择所属科室");
    return;
  }
  if (!wardForm.type.trim()) {
    ElMessage.warning("请选择病房类型");
    return;
  }
  if (
    wardForm.ward_id === null ||
    wardForm.ward_id === undefined ||
    !Number.isInteger(wardForm.ward_id) ||
    wardForm.ward_id < 101 ||
    wardForm.ward_id > 999
  ) {
    ElMessage.warning("房间号格式错误，需输入 101-999 的整数");
    return;
  }
  wardCreating.value = true;
  createWard({
    ward_id: wardForm.ward_id,
    dept_id: wardForm.dept_id,
    type: wardForm.type.trim(),
    bed_count: wardForm.bed_count
  })
    .then(() => {
      ElMessage.success("新增病房成功");
      resetWardForm();
      return loadWards();
    })
    .catch((error: any) => {
      const message = error?.response?.data?.detail;
      ElMessage.error(message || "新增病房失败");
    })
    .then(
      () => {
        wardCreating.value = false;
      },
      () => {
        wardCreating.value = false;
      }
    );
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
      doctorList.value = (data || []).map((doctor) => ({
        ...doctor,
        title: normalizeDoctorLevel((doctor as any).title)
      }));
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
  const nextTitle = normalizeDoctorLevel(typeof titleValue === "string" ? titleValue : "专家医师");
  updateDoctorTitle(doctorId, nextTitle)
    .then(() => {
      ElMessage.success("医生级别已更新");
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
  loadWards();
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
    const message = error?.response?.data?.detail;
    ElMessage.error(message || "科室数据获取失败");
  } finally {
    deptLoading.value = false;
  }
}

async function loadWards() {
  try {
    wardLoading.value = true;
    const { data } = await fetchAdminWards();
    wardList.value = data;
    const currentIds = new Set(data.map((w) => w.ward_id));
    hiddenWardIds.value = new Set(Array.from(hiddenWardIds.value).filter((id) => currentIds.has(id)));
  } catch (error: any) {
    const message = error?.response?.data?.detail;
    ElMessage.error(message || "病房数据获取失败");
  } finally {
    wardLoading.value = false;
  }
}

function handleHideWard(wardId: number) {
  const next = new Set(hiddenWardIds.value);
  if (next.has(wardId)) {
    next.delete(wardId);
  } else {
    next.add(wardId);
  }
  hiddenWardIds.value = next;
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


.import-card {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.import-instructions {
  background: #f8fafc;
  border-radius: 8px;
  padding: 12px 16px;
  color: #475569;
  line-height: 1.6;
}

.import-instructions p {
  margin: 0;
}

.import-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.upload-area {
  flex: 1;
  min-width: 220px;
}

.upload-tip {
  color: #94a3b8;
  margin-top: 4px;
}

.upload-icon {
  font-size: 32px;
  color: #2563eb;
  margin-bottom: 8px;
}

.import-summary {
  margin-top: 16px;
}

.import-error-table {
  margin-top: 16px;
}
</style>
