import { createRouter, createWebHistory, type NavigationGuardNext, type RouteLocationNormalized } from "vue-router";
import { useAuthStore } from "../stores/auth";

import LoginView from "../views/LoginView.vue";
import LayoutShell from "../components/LayoutShell.vue";
import OverviewView from "../views/dashboard/OverviewView.vue";
import DoctorDashboard from "../views/dashboard/DoctorDashboard.vue";
import NurseDashboard from "../views/dashboard/NurseDashboard.vue";
import PharmacyDashboard from "../views/dashboard/PharmacyDashboard.vue";
import AdminDashboard from "../views/dashboard/AdminDashboard.vue";
import AdminRevenue from "../views/dashboard/AdminRevenue.vue";
import StaffProfile from "../views/staff/StaffProfile.vue";
import PatientHome from "../views/patient/PatientHome.vue";
import PatientProfile from "../views/patient/PatientProfile.vue";
import PatientRegistrations from "../views/patient/PatientRegistrations.vue";
import PatientPayments from "../views/patient/PatientPayments.vue";
import PatientExaminations from "../views/patient/PatientExaminations.vue";

const roleFallback: Record<string, string> = {
  患者: "/workspace/patient/home",
  医生: "/workspace/doctor",
  护士: "/workspace/nurse",
  药师: "/workspace/pharmacy",
  管理员: "/workspace/admin"
};

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: "/login",
      name: "login",
      component: LoginView,
      meta: { public: true }
    },
    {
      path: "/",
      component: LayoutShell,
      redirect: "/workspace/overview",
      children: [
        {
          path: "workspace/overview",
          name: "overview",
          component: OverviewView,
          meta: { roles: ["医生", "护士", "药师", "管理员"] }
        },
        {
          path: "workspace/patient",
          redirect: "/workspace/patient/home",
          meta: { roles: ["患者"] }
        },
        {
          path: "workspace/patient/home",
          name: "patient-home",
          component: PatientHome,
          meta: { roles: ["患者"] }
        },
        {
          path: "workspace/patient/profile",
          name: "patient-profile",
          component: PatientProfile,
          meta: { roles: ["患者"] }
        },
        {
          path: "workspace/patient/registrations",
          name: "patient-registrations",
          component: PatientRegistrations,
          meta: { roles: ["患者"] }
        },
        {
          path: "workspace/patient/medical-records",
          name: "patient-medical-records",
          component: () => import("../views/patient/PatientMedicalRecords.vue"),
          meta: { roles: ["患者"] }
        },
        {
          path: "workspace/patient/payments",
          name: "patient-payments",
          component: PatientPayments,
          meta: { roles: ["患者"] }
        },
        {
          path: "workspace/patient/examinations",
          name: "patient-examinations",
          component: PatientExaminations,
          meta: { roles: ["患者"] }
        },
        {
          path: "workspace/doctor",
          name: "doctor",
          component: DoctorDashboard,
          meta: { roles: ["医生"] }
        },
        {
          path: "workspace/consultation/:reg_id",
          name: "consultation",
          // lazy load consultation view
          component: () => import("../views/dashboard/ConsultationView.vue"),
          meta: { roles: ["医生"] }
        },
        {
          path: "workspace/doctor/prescription/:reg_id",
          name: "doctor-prescription",
          component: () => import("../views/dashboard/DoctorPrescription.vue"),
          meta: { roles: ["医生"] }
        },
        {
          path: "workspace/doctor/profile",
          name: "doctor-profile",
          component: StaffProfile,
          meta: { roles: ["医生"] }
        },
        {
          path: "workspace/nurse",
          name: "nurse",
          component: NurseDashboard,
          meta: { roles: ["护士"] }
        },
        {
          path: "workspace/nurse/schedule-management",
          name: "nurse-schedule-management",
          component: () => import("../views/dashboard/HeadNurseSchedule.vue"),
          meta: { roles: ["护士"], headOnly: true }
        },
        {
          path: "workspace/nurse/profile",
          name: "nurse-profile",
          component: StaffProfile,
          meta: { roles: ["护士"] }
        },
        {
          path: "workspace/pharmacy",
          name: "pharmacy",
          component: PharmacyDashboard,
          meta: { roles: ["药师"] }
        },
        {
          path: "workspace/pharmacy/profile",
          name: "pharmacy-profile",
          component: StaffProfile,
          meta: { roles: ["药师"] }
        },
        {
          path: "workspace/admin",
          name: "admin",
          component: AdminDashboard,
          meta: { roles: ["管理员"] }
        }
        ,
        {
          path: "workspace/admin/revenue",
          name: "admin-revenue",
          component: AdminRevenue,
          meta: { roles: ["管理员"] }
        },
        {
          path: "workspace/admin/profile",
          name: "admin-profile",
          component: StaffProfile,
          meta: { roles: ["管理员"] }
        }
      ]
    },
    {
      path: "/:pathMatch(.*)*",
      redirect: "/"
    }
  ]
});

router.beforeEach((to: RouteLocationNormalized, _from: RouteLocationNormalized, next: NavigationGuardNext) => {
  const auth = useAuthStore();
  if (!to.meta.public && !auth.isAuthenticated) {
    next({ path: "/login", query: { redirect: to.fullPath } });
    return;
  }

  if (to.meta.roles && to.meta.roles.length) {
    if (!auth.currentRole || !to.meta.roles.includes(auth.currentRole)) {
      const fallback = roleFallback[auth.currentRole ?? ""] ?? "/workspace/overview";
      next(fallback);
      return;
    }
  }

  if (to.meta.headOnly && auth.currentRole === "护士" && !auth.isHeadNurse) {
    next("/workspace/nurse");
    return;
  }

  if (to.path === "/login" && auth.isAuthenticated) {
    const fallback = roleFallback[auth.currentRole ?? ""] ?? "/workspace/overview";
    next(fallback);
    return;
  }

  next();
});

export default router;
