import { computed, ref } from "vue";
import { defineStore } from "pinia";

import { useAuthStore } from "./auth";
import { fetchMyPayments, fetchMyRegistrations, type PaymentItem, type RegistrationItem } from "../api/modules/patient";

type NoticeItem = {
  key: string;
  kind: "payment" | "registration";
  message: string;
  createdAt: string;
  payment_id?: number;
  reg_id?: number;
};

export const useNotificationStore = defineStore("notifications", () => {
  const auth = useAuthStore();

  const notifications = ref<NoticeItem[]>([]);
  const pollingId = ref<number | null>(null);

  const isEnabled = computed(() => auth.isAuthenticated && auth.currentRole === "患者");

  function buildPaymentNotice(payment: PaymentItem): NoticeItem {
    const typeText = payment.type || "缴费";

    if (payment.status === "待退费" && typeText === "挂号费") {
      return {
        key: `payment-${payment.payment_id}`,
        kind: "payment",
        message: "您有一个挂号费可以退费",
        createdAt: new Date().toISOString(),
        payment_id: payment.payment_id
      };
    }

    return {
      key: `payment-${payment.payment_id}`,
      kind: "payment",
      message: `您有一项${typeText}待缴费`,
      createdAt: new Date().toISOString(),
      payment_id: payment.payment_id
    };
  }

  function buildTodayVisitNotice(reg: RegistrationItem): NoticeItem {
    return {
      key: `reg-${reg.reg_id}`,
      kind: "registration",
      message: "请您在今天前往就诊",
      createdAt: new Date().toISOString(),
      reg_id: reg.reg_id
    };
  }

  function parseTime(value: unknown): number {
    if (typeof value !== "string") return 0;
    const t = Date.parse(value);
    return Number.isFinite(t) ? t : 0;
  }

  function toYmd(value: unknown): string {
    if (typeof value !== "string") return "";
    return value.split("T")[0] ?? "";
  }

  function todayYmd(): string {
    const d = new Date();
    const y = d.getFullYear();
    const m = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${y}-${m}-${day}`;
  }

  function normalizeRegistrationStatus(value: unknown): string {
    const s = String(value ?? "");
    if (!s) return "";
    // Backward-compatible mapping
    if (s === "待就诊") return "排队中";
    if (s === "办理中") return "就诊中";
    if (s === "已就诊" || s === "已结束") return "已完成";
    return s;
  }

  async function syncPaymentsOnce() {
    if (!isEnabled.value) return;

    let payments: PaymentItem[] = [];
    let regs: RegistrationItem[] = [];
    try {
      const [payRes, regRes] = await Promise.all([fetchMyPayments(), fetchMyRegistrations()]);
      payments = Array.isArray(payRes.data) ? payRes.data : [];
      regs = Array.isArray(regRes.data) ? regRes.data : [];
    } catch {
      // ignore polling errors; UI should still work without hard-failing
      return;
    }

    // Always reflect current unpaid payments (including historical);
    // once paid, it disappears from the list.
    const unpaid = payments
      .filter((p) => {
        if (typeof p?.payment_id !== "number") return false;
        if (p.status === "未缴费") return true;
        if (p.status === "待退费" && p.type === "挂号费") return true;
        return false;
      })
      .sort((a, b) => {
        const tb = parseTime((b as any).time);
        const ta = parseTime((a as any).time);
        if (tb !== ta) return tb - ta;
        return (b.payment_id ?? 0) - (a.payment_id ?? 0);
      });

    const map = new Map<string, NoticeItem>();
    for (const p of unpaid) {
      const notice = buildPaymentNotice(p);
      map.set(notice.key, notice);
    }

    // Appointment-day reminder
    const today = todayYmd();
    for (const r of regs) {
      const vd = toYmd((r as any).visit_date as any);
      const status = normalizeRegistrationStatus((r as any).status);
      // Only remind when: local today matches visit_date AND still waiting (排队中).
      // Do NOT remind for "就诊中" / "已完成" / "已取消" / "已过期" etc.
      if (vd && vd === today && status === "排队中") {
        const notice = buildTodayVisitNotice(r);
        map.set(notice.key, notice);
      }
    }

    notifications.value = Array.from(map.values());

    if (notifications.value.length > 200) {
      notifications.value = notifications.value.slice(0, 200);
    }
  }

  function startPolling(intervalMs = 15000) {
    if (!isEnabled.value) return;
    if (pollingId.value !== null) return;
    void syncPaymentsOnce();

    pollingId.value = window.setInterval(() => {
      void syncPaymentsOnce();
    }, intervalMs);
  }

  function stopPolling() {
    if (pollingId.value !== null) {
      window.clearInterval(pollingId.value);
      pollingId.value = null;
    }
  }

  function clearNotifications() {
    notifications.value = [];
  }

  return {
    notifications,
    startPolling,
    stopPolling,
    clearNotifications,
    syncPaymentsOnce
  };
});
