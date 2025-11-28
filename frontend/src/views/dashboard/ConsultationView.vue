、<template>
  <div class="consultation">
    <el-card>
      <div style="display:flex; justify-content:space-between; align-items:center; gap:12px;">
        <div>
          <h3>接诊 - 挂号 {{ regId }}</h3>
          <div v-if="patient">
            <small>患者：{{ patient.name }} （ID: {{ patient.patient_id }}）</small>
          </div>
        </div>
        <div>
          <el-button type="default" @click="onExit" style="margin-right:8px">退出接诊</el-button>
        </div>
      </div>
    </el-card>

    <el-card class="mt-3">
      <div class="option-grid">
        <div class="option-row">
          <div class="option-col">
            <el-card class="option-card" :body-style="{ padding: '8px' }">
              <div style="display:flex; align-items:center; gap:8px">
                <Document class="option-icon" />
                <div>
                  <div style="font-weight:700; font-size:14px">书写病历</div>
                  <div style="color:var(--el-text-color-secondary); font-size:12px">查看或编辑当前挂号的病历</div>
                </div>
              </div>
              <div class="action-row">
                <el-button type="primary" size="small" @click.stop="openRecordDialog">书写</el-button>
              </div>
            </el-card>
          </div>

          <div class="option-col">
            <el-card class="option-card" :body-style="{ padding: '8px' }">
              <div style="display:flex; align-items:center; gap:8px">
                <FirstAidKit class="option-icon" />
                <div>
                  <div style="font-weight:700; font-size:14px">开具检查</div>
                  <div style="color:var(--el-text-color-secondary); font-size:12px">为患者申请检验或影像检查</div>
                </div>
              </div>
              <div class="action-row">
                <el-button type="warning" size="small" @click="onCreateExam">开具</el-button>
              </div>
            </el-card>
          </div>

          <div class="option-col">
            <el-card class="option-card" :body-style="{ padding: '8px' }">
              <div style="display:flex; align-items:center; gap:8px">
                <List class="option-icon" />
                <div>
                  <div style="font-weight:700; font-size:14px">开具处方</div>
                  <div style="color:var(--el-text-color-secondary); font-size:12px">为患者选药并生成处方（会反映库存）</div>
                </div>
              </div>
              <div class="action-row">
                <el-button type="success" size="small" @click="onOpenPrescription">开具</el-button>
              </div>
            </el-card>
          </div>

          <div class="option-col">
            <el-card class="option-card" :body-style="{ padding: '8px' }">
              <div style="display:flex; align-items:center; gap:8px">
                <View class="option-icon" />
                <div>
                  <div style="font-weight:700; font-size:14px">办理住院</div>
                  <div style="color:var(--el-text-color-secondary); font-size:12px">为患者办理住院手续</div>
                </div>
              </div>
              <div class="action-row">
                <el-button type="info" size="small" @click="onAdmit">办理</el-button>
              </div>
            </el-card>
          </div>

          <div class="option-col">
            <el-card class="option-card" :body-style="{ padding: '8px' }">
              <div style="display:flex; align-items:center; gap:8px">
                <CreditCard class="option-icon" />
                <div>
                  <div style="font-weight:700; font-size:14px">完成办理</div>
                  <div style="color:var(--el-text-color-secondary); font-size:12px">结束本次接诊并归档</div>
                </div>
              </div>
              <div class="action-row">
                <el-button type="danger" size="small" :loading="finishing" @click="onFinish">完成</el-button>
              </div>
            </el-card>
          </div>
        </div>
      </div>
    </el-card>

    <el-dialog v-model="recordDialogVisible" title="书写病历" width="520px">
      <el-form :model="recordForm" label-width="90px">
        <el-form-item label="主诉">
          <el-input v-model="recordForm.complaint" type="textarea" rows="2" />
        </el-form-item>
        <el-form-item label="诊断结果">
          <el-input v-model="recordForm.diagnosis" type="textarea" rows="2" />
        </el-form-item>
        <el-form-item label="治疗建议">
          <el-input v-model="recordForm.suggestion" type="textarea" rows="2" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="recordDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="recordLoading" @click="submitRecord">保存并完成</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="examDialogVisible" title="开具检查" width="420px">
      <el-form label-width="100px">
        <el-form-item label="检查类型">
          <el-input v-model="examType" placeholder="例如：血常规 / CT" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="examDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="examLoading" @click="submitExam">开具并生成结果</el-button>
      </template>
    </el-dialog>

    <el-card class="mt-3">
      <h4>检查记录</h4>
      <div v-if="exams.length === 0">
        <small class="muted">当前无检查记录</small>
      </div>
      <el-timeline v-else>
        <el-timeline-item v-for="e in exams" :key="e.exam_id" :timestamp="new Date(e.date).toLocaleString()">
          <div style="display:flex;justify-content:space-between;align-items:center;gap:12px;">
            <div>
              <div style="font-weight:600">{{ e.type }}</div>
              <div style="color:var(--el-text-color-secondary);font-size:12px">结果：{{ e.result }}</div>
            </div>
          </div>
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { onMounted, reactive, ref } from "vue";
import { FirstAidKit, Document, List, View, CreditCard } from "@element-plus/icons-vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { startHandling, finishHandling, submitMedicalRecord, fetchConsultationInfo, fetchMedicalRecordByReg, createExamination, fetchExaminations } from "../../api/modules/doctor";
import { fetchPatientById } from "../../api/modules/patient";

const route = useRoute();
const router = useRouter();
const regId = Number(route.params.reg_id || route.query.reg_id || 0);

const patientId = Number(route.query.patient_id || 0);

const patient = ref(null as any);
const recordDialogVisible = ref(false);
const recordLoading = ref(false);
const finishing = ref(false);

const recordForm = reactive({ complaint: "", diagnosis: "", suggestion: "" });
const exams = ref([] as Array<any>);
const examDialogVisible = ref(false);
const examType = ref("");
const examLoading = ref(false);

async function ensureStarted() {
  // 检查挂号当前状态，仅在仍为“排队中/待就诊/WAITING”时才调用 startHandling
  try {
    const { data } = await fetchConsultationInfo(regId);
    const reg = data?.registration;
    if (data?.patient) {
      patient.value = data.patient;
    }
    const status = reg?.status;
    if (isWaitingStatus(status)) {
      try {
        await startHandling(regId);
        ElMessage.success("已开始办理");
      } catch (err: any) {
        const msg = err?.response?.data?.detail;
        if (msg && !msg.includes("只有排队中的挂号可以开始办理")) {
          ElMessage.error(msg ?? "开始办理失败");
        }
      }
    } else {
      // 如果不是等待状态，直接进入接诊页继续操作
    }
  } catch (err: any) {
    // 若后端 info 接口不可用或返回错误，回退到原有行为：尝试用 query patientId 加载患者信息
    const msg = err?.response?.data?.detail ?? err?.message ?? null;
    if (msg) {
      console.debug("fetchConsultationInfo failed:", msg);
    }
    // 继续，不阻塞页面
  }
}

function isWaitingStatus(s: string | null | undefined) {
  if (!s) return false;
  const v = String(s).toLowerCase();
  return v === "排队中" || v === "待就诊" || v === "waiting" || v === "wait";
}

async function loadPatient() {
  // 优先通过 query 中的 patient_id 获取患者；如果没有，则请求后端的 consultation info
  if (patientId) {
    try {
      const { data } = await fetchPatientById(patientId);
      patient.value = data;
      return;
    } catch (err) {
      // fallback to consultation info
    }
  }

  try {
    const { data } = await fetchConsultationInfo(regId);
    // data.patient 包含患者信息
    patient.value = data.patient;
  } catch (err) {
    // ignore — 页面仍然可用
  }
}

async function openRecordDialog() {
  // 尝试拉取已有病历并填充表单
  try {
    const { data } = await fetchMedicalRecordByReg(regId);
    recordForm.complaint = data.complaint || "";
    recordForm.diagnosis = data.diagnosis || "";
    recordForm.suggestion = data.suggestion || "";
  } catch (err: any) {
    // 404 表示没有病历，清空表单以便新建
    if (!(err?.response?.status === 404)) {
      console.warn("加载已有病历失败", err);
      ElMessage.error(err?.response?.data?.detail ?? "加载病历失败");
    } else {
      recordForm.complaint = "";
      recordForm.diagnosis = "";
      recordForm.suggestion = "";
    }
  }
  recordDialogVisible.value = true;
}

async function loadExams() {
  try {
    const { data } = await fetchExaminations(regId);
    exams.value = data || [];
  } catch (err: any) {
    // ignore if not available yet
    exams.value = [];
  }
}

async function submitRecord() {
  if (!recordForm.complaint || !recordForm.diagnosis) {
    ElMessage.warning("主诉和诊断为必填项");
    return;
  }
  recordLoading.value = true;
  try {
    const { data } = await submitMedicalRecord(regId, { ...recordForm });
    ElMessage.success(`病历提交成功，记录号 ${data.record_id}`);
    recordDialogVisible.value = false;
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail ?? "提交病历失败");
  } finally {
    recordLoading.value = false;
  }
}

async function onOpenPrescription() {
  // 始终跳转到医生处方页面，新页面会在必要时自动建立最小病历并提交处方
  router.push({ name: "doctor-prescription", params: { reg_id: String(regId) } });
}

async function onCreateExam() {
  // open dialog to enter exam type
  examType.value = "";
  examDialogVisible.value = true;
}

async function submitExam() {
  if (!examType.value) {
    ElMessage.warning("请填写检查类型");
    return;
  }
  examLoading.value = true;
  try {
    const { data } = await createExamination(regId, { type: examType.value });
    // backend returns created exam with randomized result
    exams.value.unshift(data);
    ElMessage.success(`检查已开具：结果 ${data.result}`);
    examDialogVisible.value = false;
  } catch (err: any) {
    ElMessage.error(err?.response?.data?.detail ?? "开具检查失败");
  } finally {
    examLoading.value = false;
  }
}

async function onAdmit() {
  ElMessage.info("办理住院功能暂未实现（占位）");
}

async function onFinish() {
  finishing.value = true;
  try {
    await finishHandling(regId);
    ElMessage.success("已完成办理");
    router.push({ path: "/workspace/doctor" });
  } catch (err: any) {
    ElMessage.error(err.response?.data?.detail ?? "完成办理失败");
  } finally {
    finishing.value = false;
  }
}

function onExit() {
  // 仅退出接诊页面，不改变挂号状态（保持为就诊中）
  ElMessage.info("已退出接诊，挂号仍为就诊中，可在医生端继续处理");
  router.push({ path: "/workspace/doctor" });
}

onMounted(async () => {
  await ensureStarted();
  await loadPatient();
  await loadExams();
});
</script>

<style scoped>
.mt-3 {
  margin-top: 16px;
}

.option-grid {
  --card-bg: #ffffff;
}
.option-card {
  cursor: pointer;
  transition: box-shadow .18s ease, transform .12s ease;
  border-radius: 8px;
}
.option-card:hover {
  box-shadow: 0 6px 14px rgba(13,27,42,0.10);
  transform: translateY(-2px);
}
.option-icon {
  font-size: 20px;
  color: var(--el-color-primary);
}

.option-row {
  display: flex;
  gap: 8px;
  justify-content: space-between;
  align-items: stretch;
  flex-wrap: wrap;
}
.option-col {
  flex: 0 0 calc(20% - 6.4px);
  box-sizing: border-box;
}
@media (max-width: 900px) {
  .option-col { flex: 0 0 48%; margin-bottom:8px; }
}
@media (max-width: 600px) {
  .option-col { flex: 0 0 100%; }
}

/* Ensure cards are equal height and internal layout places action at bottom */
.option-card {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100%;
}
.option-card > .el-card__body {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  height: 100%;
  padding: 8px !important;
}
.option-col { min-height: 84px; }

/* Align action button to card bottom/right */
.action-row {
  margin-top: 8px;
  display: flex;
  justify-content: flex-end;
  align-items: flex-end;
}

.mt-3 { margin-top: 16px; }
</style>
