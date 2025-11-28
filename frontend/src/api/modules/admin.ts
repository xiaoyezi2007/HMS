import http from "../http";

export interface StaffAccount {
  phone: string;
  username: string;
  role: string;
  status: string;
  register_time: string;
}

export interface StaffAccountPayload {
  phone: string;
  username: string;
  role: string;
  dept_id?: number;
}

export interface DepartmentItem {
  dept_id: number;
  dept_name: string;
  telephone?: string;
}

export interface DoctorProfile {
  doctor_id: number;
  name: string;
  gender: string;
  title: string;
  phone: string;
  dept_id?: number;
  dept_name?: string;
}

export interface NurseProfile {
  nurse_id: number;
  name: string;
  gender: string;
  phone: string;
  is_head_nurse: boolean;
}

export function fetchStaffAccounts(role?: string) {
  if (role) {
    return http.get<StaffAccount[]>("/api/admin/accounts", { params: { role } });
  }
  return http.get<StaffAccount[]>("/api/admin/accounts");
}

export function createStaffAccount(payload: StaffAccountPayload) {
  return http.post<StaffAccount>("/api/admin/accounts", payload);
}

export function fetchDepartments() {
  return http.get<DepartmentItem[]>("/api/departments");
}

export function deleteStaffAccount(phone: string) {
  return http.delete(`/api/admin/accounts/${phone}`);
}

export function fetchDoctors() {
  return http.get<DoctorProfile[]>("/api/admin/doctors");
}

export function updateDoctorTitle(doctorId: number, title: string) {
  return http.patch(`/api/admin/doctors/${doctorId}/title`, { title });
}

export function fetchNurses() {
  return http.get<NurseProfile[]>("/api/admin/nurses");
}

export function updateNurseHeadStatus(nurseId: number, isHead: boolean) {
  return http.patch(`/api/admin/nurses/${nurseId}/head`, { is_head_nurse: isHead });
}
