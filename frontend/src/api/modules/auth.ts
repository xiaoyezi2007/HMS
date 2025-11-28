import http from "../http";

export interface LoginPayload {
  phone: string;
  password: string;
}

export interface RegisterPayload {
  phone: string;
  username: string;
  password: string;
  role: string;
}

export async function login(payload: LoginPayload) {
  const formData = new FormData();
  formData.append("username", payload.phone);
  formData.append("password", payload.password);
  return http.post("/auth/login", formData, {
    headers: { "Content-Type": "multipart/form-data" }
  });
}

export async function register(payload: RegisterPayload) {
  return http.post("/auth/register", payload);
}

export function fetchCurrentUser() {
  return http.get("/auth/me");
}

export function changePassword(current_password: string, new_password: string) {
  return http.post("/auth/change-password", { current_password, new_password });
}
