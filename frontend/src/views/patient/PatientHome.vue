<template>
  <div class="patient-home">
    <el-row :gutter="16">
      <el-col v-for="card in cards" :key="card.path" :lg="12" :md="12" :sm="12" :xs="24">
        <el-card shadow="hover" class="card" @click="go(card.path)">
          <div class="card-icon" :style="{ background: card.bg }">
            <component :is="card.icon" />
          </div>
          <h3>{{ card.title }}</h3>
          <p>{{ card.desc }}</p>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { User, Tickets, CreditCard, View } from "@element-plus/icons-vue";

const cards = [
  { title: "我的挂号", desc: "提交新的挂号申请并查看状态", path: "/workspace/patient/registrations", icon: Tickets, bg: "#ede9fe" },
  { title: "缴费查询", desc: "检索历史缴费记录，掌握费用明细", path: "/workspace/patient/payments", icon: CreditCard, bg: "#d1fae5" },
  { title: "检查结果", desc: "随时掌握检查报告与参考值", path: "/workspace/patient/examinations", icon: View, bg: "#fee2e2" },
  { title: "个人主页", desc: "完善实名档案与联系方式", path: "/workspace/patient/profile", icon: User, bg: "#e0f2fe" }
];

const router = useRouter();

function go(path: string) {
  router.push(path);
}
</script>

<style scoped>
.patient-home {
  padding: 16px 0;
}

.card {
  cursor: pointer;
  transition: transform 0.2s ease;
  min-height: 160px;
}

.card:hover {
  transform: translateY(-4px);
}

.card-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: 12px;
}

.card-icon :deep(svg) {
  width: 24px;
  height: 24px;
}

.card h3 {
  margin: 0 0 8px;
}
</style>
