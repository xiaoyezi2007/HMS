import { computed, ref } from "vue";
import { defineStore } from "pinia";
import { jwtDecode } from "jwt-decode";

interface TokenPayload {
  sub?: string;
  role?: string;
  exp?: number;
}

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string>(window.localStorage.getItem("hms-token") ?? "");
  const role = ref<string>(window.localStorage.getItem("hms-role") ?? "");
  const phone = ref<string>(window.localStorage.getItem("hms-phone") ?? "");
  const headNurseFlag = ref<boolean>((window.localStorage.getItem("hms-head-nurse") ?? "0") === "1");

  const isAuthenticated = computed(() => Boolean(token.value));
  const currentRole = computed(() => role.value);
  const isHeadNurse = computed(() => headNurseFlag.value);

  function setSession(tokenValue: string, fallbackPhone: string) {
    let decoded: TokenPayload = {};
    try {
      decoded = jwtDecode<TokenPayload>(tokenValue);
    } catch (err) {
      console.warn("解析 Token 失败", err);
    }

    const phoneValue = decoded.sub ?? fallbackPhone;
    const roleValue = decoded.role ?? role.value;

    token.value = tokenValue;
    phone.value = phoneValue;
    role.value = roleValue ?? "";
    if (role.value !== "护士") {
      setHeadNurseFlag(false);
    }

    window.localStorage.setItem("hms-token", tokenValue);
    window.localStorage.setItem("hms-phone", phoneValue ?? "");
    window.localStorage.setItem("hms-role", role.value);
  }

  function setRole(roleValue: string) {
    role.value = roleValue;
    window.localStorage.setItem("hms-role", roleValue);
    if (roleValue !== "护士") {
      setHeadNurseFlag(false);
    }
  }

  function setHeadNurseFlag(flag: boolean) {
    headNurseFlag.value = flag;
    if (flag) {
      window.localStorage.setItem("hms-head-nurse", "1");
    } else {
      window.localStorage.removeItem("hms-head-nurse");
    }
  }

  function logout() {
    token.value = "";
    role.value = "";
    phone.value = "";
    headNurseFlag.value = false;
    window.localStorage.removeItem("hms-token");
    window.localStorage.removeItem("hms-role");
    window.localStorage.removeItem("hms-phone");
    window.localStorage.removeItem("hms-head-nurse");
  }

  return {
    token,
    role,
    phone,
    headNurseFlag,
    isAuthenticated,
    currentRole,
    isHeadNurse,
    setSession,
    setRole,
    setHeadNurseFlag,
    logout
  };
});
