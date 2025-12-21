<template>
  <div class="patient-module">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>缴费查询</span>
          <small>查看并完成未缴费项</small>
        </div>
      </template>
      <div>
        <div v-if="payments.length">
          <el-table :data="payments" style="width: 100%">
            <el-table-column prop="type" label="类型" width="120" />
            <el-table-column prop="amount" label="金额" width="100">
              <template #default="{ row }">¥{{ row.amount }}</template>
            </el-table-column>
            <el-table-column prop="time" label="时间">
              <template #default="{ row }">{{ formatDateTimeText(row.time) }}</template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="100" />
            <el-table-column label="操作" width="140">
              <template #default="{ row }">
                <el-button
                  v-if="canPay(row)"
                  size="small"
                  type="primary"
                  @click="doPay(row)"
                >
                  缴费
                </el-button>
                <el-button
                  v-else-if="canRefund(row)"
                  size="small"
                  type="warning"
                  @click="doRefund(row)"
                >
                  退费
                </el-button>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="附加信息">
              <template #default="{ row }">
                <div v-if="row.exam_info">
                  <strong>检查：</strong>{{ row.exam_info.type }}
                  <div v-if="row.exam_info.result">结果：{{ row.exam_info.result }}</div>
                  <div v-if="row.exam_info.date">时间：{{ formatDateTimeText(row.exam_info.date) }}</div>
                </div>
                <div v-else-if="row.prescription_info">
                  <strong>处方：</strong>
                  <div v-if="row.prescription_info.details.length">
                    <div v-for="detail in row.prescription_info.details" :key="detail.medicine_id">
                      {{ detail.medicine_name || '未知药品' }} × {{ detail.quantity }}
                      <span v-if="detail.usage">（{{ detail.usage }}）</span>
                    </div>
                  </div>
                  <div v-else>处方内容未记录</div>
                </div>
                <div v-else-if="row.hospitalization_info">
                  <strong>住院：</strong>{{ row.hospitalization_info.ward_type || '住院病房' }}
                  <div>入院：{{ formatDate(row.hospitalization_info.in_date) }}</div>
                  <div v-if="row.hospitalization_info.out_date">出院：{{ formatDate(row.hospitalization_info.out_date) }}</div>
                  <div>时长：{{ formatDuration(row.hospitalization_info.duration_hours) }}</div>
                  <el-tag
                    v-if="row.hospitalization_bill"
                    size="small"
                    type="info"
                    class="bill-tag"
                  >
                    合计 ¥{{ formatCurrency(row.hospitalization_bill.total_fee) }}
                  </el-tag>
                  <el-button
                    v-if="row.hospitalization_bill"
                    link
                    type="primary"
                    @click="showBillDetail(row)"
                    class="bill-link"
                  >
                    查看费用详情
                  </el-button>
                </div>
                <div v-else-if="row.type === '挂号费'">挂号费用</div>
              </template>
            </el-table-column>
          </el-table>
        </div>

        <div v-else>
          <el-result icon="warning" title="暂无缴费记录" sub-title="暂无待缴或历史缴费记录" />
        </div>
      </div>

      <el-dialog
        v-model="detailVisible"
        width="700px"
        destroy-on-close
        :close-on-click-modal="false"
        title="住院费用详情"
      >
        <template v-if="selectedPayment && selectedPayment.hospitalization_bill">
          <div class="bill-section">
            <div class="bill-head">
              <span>{{ selectedPayment.hospitalization_info?.ward_type || '住院病房' }}</span>
              <span>合计 ¥{{ formatCurrency(selectedPayment.hospitalization_bill.total_fee) }}</span>
            </div>
            <div class="bill-summary">
              <span>基础 ¥{{ formatCurrency(selectedPayment.hospitalization_bill.base_fee) }} · {{ formatHours(selectedPayment.hospitalization_bill.base_hours) }}</span>
              <span>药品 ¥{{ formatCurrency(selectedPayment.hospitalization_bill.medicine_fee) }}</span>
              <span>护理/服务 ¥{{ formatCurrency(selectedPayment.hospitalization_bill.service_fee) }}</span>
            </div>
            <div class="bill-meta">
              <span>入院：{{ formatDate(selectedPayment.hospitalization_info?.in_date) }}</span>
              <span v-if="selectedPayment.hospitalization_info?.out_date">出院：{{ formatDate(selectedPayment.hospitalization_info?.out_date) }}</span>
              <span>时长：{{ formatDuration(selectedPayment.hospitalization_info?.duration_hours) }}</span>
            </div>
          </div>
          <div class="bill-task-list" v-if="selectedPayment.hospitalization_bill.tasks?.length">
            <div
              v-for="task in selectedPayment.hospitalization_bill.tasks"
              :key="task.task_id"
              class="bill-task-item"
            >
              <div class="task-main">
                <div>
                  <span class="task-type">{{ formatDateTimeText(task.time) }}</span>
                  <span> · {{ task.type }}</span>
                  <span v-if="task.status">（{{ task.status }}）</span>
                </div>
                <div class="task-amount">¥{{ formatCurrency(task.total_fee) }}</div>
              </div>
              <div class="task-detail" v-if="task.detail">{{ task.detail }}</div>
              <div class="task-fee">药品 ¥{{ formatCurrency(task.medicine_fee) }} ｜ 服务 ¥{{ formatCurrency(task.service_fee) }}</div>
              <div class="task-meds" v-if="task.medicines && task.medicines.length">
                <span v-for="med in task.medicines" :key="med.medicine_id">
                  {{ med.name || '药品' }} × {{ med.quantity }}（¥{{ formatCurrency(med.subtotal) }}）
                </span>
              </div>
            </div>
          </div>
        </template>
        <template v-else>
          <el-empty description="暂无明细" />
        </template>
        <template #footer>
          <el-button @click="detailVisible = false">关闭</el-button>
        </template>
      </el-dialog>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { fetchMyPayments, payPayment, refundPayment } from '../../api/modules/patient'
import type { PaymentItem } from '../../api/modules/patient'

const payments = ref<PaymentItem[]>([])
const detailVisible = ref(false)
const selectedPayment = ref<PaymentItem | null>(null)

function formatDateTimeText(value?: unknown) {
  if (value === undefined || value === null) return '-'
  return String(value).replace('T', ' ')
}

function parseTime(value: unknown): number {
  if (typeof value !== 'string') return 0
  const t = Date.parse(value)
  return Number.isFinite(t) ? t : 0
}

async function load() {
  try {
    const res = await fetchMyPayments()
    const list = Array.isArray(res.data) ? res.data : []
    payments.value = list.sort((a: PaymentItem, b: PaymentItem) => {
      const tb = parseTime(b?.time)
      const ta = parseTime(a?.time)
      if (tb !== ta) return tb - ta
      return (b?.payment_id ?? 0) - (a?.payment_id ?? 0)
    })
  } catch (e) {
    console.error(e)
    ElMessage.error('获取缴费记录失败')
  }
}

async function doPay(row: PaymentItem) {
  try {
    await payPayment(row.payment_id)
    ElMessage.success('缴费成功')
    await load()
  } catch (e: any) {
    console.error(e)
    const msg = e?.response?.data?.detail || '缴费失败'
    ElMessage.error(msg)
  }
}

async function doRefund(row: PaymentItem) {
  try {
    await refundPayment(row.payment_id)
    ElMessage.success('退费成功')
    await load()
  } catch (e: any) {
    console.error(e)
    const msg = e?.response?.data?.detail || '退费失败'
    ElMessage.error(msg)
  }
}

function canPay(row: PaymentItem) {
  return row?.status === '未缴费'
}

function canRefund(row: PaymentItem) {
  return row?.type === '挂号费' && row?.status === '待退费'
}

function formatDate(value?: string) {
  if (!value) return '-'
  try {
    return formatDateTimeText(value)
  } catch {
    return value
  }
}

function formatDuration(hours?: number) {
  if (hours === undefined || hours === null) return '-'
  if (hours < 24) {
    return `${hours.toFixed(1)} 小时`
  }
  return `${(hours / 24).toFixed(1)} 天`
}

function formatCurrency(value?: number | null) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '-'
  return value.toFixed(2)
}

function formatHours(value?: number | null) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '-'
  if (value >= 24) {
    return `${(value / 24).toFixed(1)} 天`
  }
  return `${value.toFixed(1)} 小时`
}

function showBillDetail(row: PaymentItem) {
  selectedPayment.value = row
  detailVisible.value = true
}

onMounted(() => {
  load()
})
</script>

<style scoped>
.card-header {
  display: flex;
  flex-direction: column;
}
.card-header small {
  color: #94a3b8;
}

.bill-tag {
  margin-top: 6px;
}

.bill-link {
  margin-left: 8px;
  font-size: 13px;
}

.bill-section {
  margin-top: 8px;
  padding: 8px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
}

.bill-head {
  display: flex;
  justify-content: space-between;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 6px;
}

.bill-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
  color: #475569;
  margin-bottom: 8px;
}

.bill-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: #475569;
  margin-bottom: 4px;
}

.bill-task-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.bill-task-item {
  border-top: 1px dashed #cbd5f5;
  padding-top: 6px;
}

.task-main {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  color: #1e293b;
}

.task-amount {
  font-weight: 600;
  color: #0f172a;
}

.task-detail {
  margin-top: 4px;
  color: #475569;
}

.task-fee {
  margin-top: 2px;
  font-size: 12px;
  color: #64748b;
}

.task-meds {
  margin-top: 4px;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  font-size: 12px;
  color: #334155;
}
</style>
