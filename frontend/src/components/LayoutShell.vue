<template>
  <div class="layout-shell">
    <el-container>
      <el-aside width="220px" class="shell-aside">
        <div class="logo">
          <strong>HMS</strong>
          <small>医院管理系统</small>
        </div>
        <el-menu :default-active="activePath" @select="handleSelect" class="menu">
          <el-menu-item v-for="item in availableMenu" :key="item.path" :index="item.path">
            <component :is="item.icon" class="menu-icon" />
            <span>{{ item.label }}</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      <el-container>
        <el-header class="shell-header">
          <div class="header-left">
            <el-breadcrumb separator="/">
              <el-breadcrumb-item>医院管理系统</el-breadcrumb-item>
              <el-breadcrumb-item>{{ currentMenuLabel }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
          <div class="header-right">
            <el-tag type="success" effect="dark">{{ auth.currentRole || "未分配角色" }}</el-tag>
            <el-divider direction="vertical" />
            <span class="phone">{{ auth.phone || "未绑定手机号" }}</span>
            <el-button type="danger" link @click="onLogout">退出登录</el-button>
          </div>
        </el-header>
        <el-main class="shell-main">
          <RouterView />
        </el-main>
      </el-container>
    </el-container>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, watch } from "vue";
import { useRouter, useRoute } from "vue-router";
import { House, User, FirstAidKit, Tickets, List, Management, Document, CreditCard, View, Coin } from "@element-plus/icons-vue";
import { useAuthStore } from "../stores/auth";
import { fetchNurseProfile } from "../api/modules/nurse";

interface MenuItem {
  path: string;
  label: string;
  roles: string[];
  icon: any;
  headOnly?: boolean;
}

const router = useRouter();
const route = useRoute();
const auth = useAuthStore();

const menuConfig: MenuItem[] = [
  { path: "/workspace/overview", label: "系统总览", roles: ["医生", "护士", "药师", "管理员"], icon: House },
  { path: "/workspace/patient/home", label: "首页", roles: ["患者"], icon: House },
  { path: "/workspace/patient/profile", label: "个人主页展示", roles: ["患者"], icon: User },
  { path: "/workspace/patient/registrations", label: "我的挂号", roles: ["患者"], icon: Tickets },
  { path: "/workspace/patient/payments", label: "缴费查询", roles: ["患者"], icon: CreditCard },
  { path: "/workspace/patient/examinations", label: "检查结果查询", roles: ["患者"], icon: View },
  { path: "/workspace/doctor", label: "医生工作站", roles: ["医生"], icon: FirstAidKit },
  { path: "/workspace/doctor/profile", label: "个人主页", roles: ["医生"], icon: User },
  { path: "/workspace/nurse", label: "护士工作站", roles: ["护士"], icon: Tickets },
  { path: "/workspace/nurse/schedule-management", label: "排班管理", roles: ["护士"], icon: Document, headOnly: true },
  { path: "/workspace/nurse/profile", label: "个人主页", roles: ["护士"], icon: User },
  { path: "/workspace/pharmacy", label: "库存管理", roles: ["药师"], icon: List },
  { path: "/workspace/pharmacy/profile", label: "个人主页", roles: ["药师"], icon: User },
  { path: "/workspace/admin", label: "管理驾驶舱", roles: ["管理员"], icon: Management },
  { path: "/workspace/admin/revenue", label: "营收记录", roles: ["管理员"], icon: Coin },
  { path: "/workspace/admin/profile", label: "个人主页", roles: ["管理员"], icon: User }
];

const availableMenu = computed(() =>
  menuConfig.filter((item: MenuItem) => {
    if (!auth.currentRole) {
      return item.roles.length > 0 && !item.headOnly;
    }
    if (item.roles.indexOf(auth.currentRole) === -1) {
      return false;
    }
    if (item.headOnly && !auth.isHeadNurse) {
      return false;
    }
    return true;
  })
);

const activePath = computed(() => route.path);

const currentMenuLabel = computed(() => {
  let found: MenuItem | undefined;
  for (const item of menuConfig) {
    if (item.path === route.path) {
      found = item;
      break;
    }
  }
  return found ? found.label : "系统总览";
});

function handleSelect(path: string) {
  router.push(path);
}

function onLogout() {
  auth.logout();
  router.replace("/login");
}

async function syncHeadNurseStatus() {
  if (!auth.isAuthenticated || auth.currentRole !== "护士") {
    auth.setHeadNurseFlag(false);
    return;
  }
  try {
    const { data } = await fetchNurseProfile();
    auth.setHeadNurseFlag(Boolean(data.is_head_nurse));
  } catch (err) {
    console.warn("fetchNurseProfile failed", err);
    auth.setHeadNurseFlag(false);
  }
}

onMounted(() => {
  void syncHeadNurseStatus();
});

watch(
  () => [auth.currentRole, auth.isAuthenticated],
  () => {
    void syncHeadNurseStatus();
  }
);
</script>

<style scoped>
.layout-shell {
  min-height: 100vh;
}

.shell-aside {
  background: #0d1b2a;
  color: #fff;
}

.logo {
  padding: 24px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.logo strong {
  display: block;
  font-size: 20px;
}

.logo small {
  color: rgba(255, 255, 255, 0.6);
}

.menu {
  border-right: none;
  background: transparent;
}

.menu :deep(.el-menu-item) {
  color: rgba(255, 255, 255, 0.8);
}

.menu :deep(.el-menu-item.is-active) {
  background-color: rgba(255, 255, 255, 0.1);
}

.menu-icon {
  margin-right: 8px;
}

.shell-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #fff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #334155;
}

.phone {
  font-weight: 600;
}

.shell-main {
  background: #f5f6fa;
  min-height: calc(100vh - 64px);
}
</style>
