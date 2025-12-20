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

export interface WardItem {
  ward_id: number;
  dept_id: number;
  dept_name: string;
  bed_count: number;
  type: string;
}

export interface DepartmentCreatePayload {
  dept_name: string;
  telephone?: string;
}

export interface WardCreatePayload {
  ward_id: number;
  dept_id: number;
  bed_count: number;
  type: string;
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

export interface RevenueTypeStat {
  type: string;
  amount: number;
  count: number;
}

export interface RevenueRecord {
  payment_id: number;
  type: string;
  amount: number;
  time: string;
  patient_id: number;
  patient_name?: string;
  patient_phone?: string;
  pres_id?: number | null;
  exam_id?: number | null;
  hosp_id?: number | null;
}

export interface RevenueSummary {
  total_amount: number;
  paid_count: number;
  by_type: RevenueTypeStat[];
  records: RevenueRecord[];
}

export interface AccountImportError {
  row_number: number;
  message: string;
}

export interface AccountImportSuccessItem {
  row_number: number;
  phone: string;
  username: string;
  role: string;
}

export interface AccountImportResult {
  total_rows: number;
  success_count: number;
  success_items: AccountImportSuccessItem[];
  errors: AccountImportError[];
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

export function createDepartment(payload: DepartmentCreatePayload) {
  return http.post<DepartmentItem>("/api/admin/departments", payload);
}

export function fetchDepartments() {
  return http.get<DepartmentItem[]>("/api/departments");
}

export function fetchAdminWards() {
  return http.get<WardItem[]>("/api/admin/wards");
}

export function createWard(payload: WardCreatePayload) {
  return http.post<WardItem>("/api/admin/wards", payload);
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

export function fetchRevenueSummary() {
  return http.get<RevenueSummary>('/api/admin/revenue');
}

export function downloadAccountTemplate() {
  return http.get<Blob>('/api/admin/accounts/template', { responseType: 'blob' });
}

export function importStaffAccounts(formData: FormData) {
  return http.post<AccountImportResult>('/api/admin/accounts/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  });
}
