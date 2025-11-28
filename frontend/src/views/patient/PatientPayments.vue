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
        <el-table v-if="payments.length" :data="payments" style="width: 100%">
          <el-table-column prop="type" label="类型" width="120" />
          <el-table-column prop="amount" label="金额" width="100">
            <template #default="{ row }">¥{{ row.amount }}</template>
          </el-table-column>
          <el-table-column prop="time" label="时间" />
          <el-table-column prop="status" label="状态" width="100" />
          <el-table-column label="操作" width="140">
            <template #default="{ row }">
              <el-button size="small" type="primary" @click="doPay(row)" :disabled="row.status === '已缴费'">缴费</el-button>
            </template>
          </el-table-column>
          <el-table-column label="附加信息">
            <template #default="{ row }">
              <div v-if="row.exam_info">
                <strong>检查：</strong>{{ row.exam_info.type }}
                <div v-if="row.exam_info.result">结果：{{ row.exam_info.result }}</div>
                <div v-if="row.exam_info.date">时间：{{ new Date(row.exam_info.date).toLocaleString() }}</div>
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
              <div v-else-if="row.type === '挂号费'">挂号费用</div>
            </template>
          </el-table-column>
        </el-table>

        <div v-else>
          <el-result icon="warning" title="暂无缴费记录" sub-title="暂无待缴或历史缴费记录" />
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { fetchMyPayments, payPayment } from '@/api/modules/patient'
import { ElMessage } from 'element-plus'

const payments = ref<Array<any>>([])

async function load() {
  try {
    const res = await fetchMyPayments()
    payments.value = res.data || []
  } catch (e) {
    console.error(e)
    ElMessage.error('获取缴费记录失败')
  }
}

async function doPay(row: any) {
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
</style>
