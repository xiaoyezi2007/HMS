import http from "../http";

export interface RegistrationItem {
  reg_id: number;
  reg_date: string;
  visit_date?: string;
  reg_type: string;
  fee: number;
  status: string;
  patient_id: number;
  doctor_id: number;
}

export interface MedicalRecordPayload {
  complaint: string;
  diagnosis: string;
  suggestion?: string;
}

export interface WardInfo {
  ward_id: number;
  type: string;
  bed_count: number;
  occupied: number;
  available: number;
  is_full: boolean;
}

export interface DoctorInpatientItem {
  hosp_id: number;
  patient_id: number;
  patient_name: string;
  ward_id: number;
  ward_type: string;
  in_date: string;
  stay_hours: number;
  reg_id: number;
}

export interface DoctorBrief {
  doctor_id: number;
  name: string;
  title?: string;
}

export interface NurseTaskMedicineItemPayload {
  medicine_id: number;
  name?: string;
  quantity: number;
  usage: string;
}

export interface NurseTaskPlanPayload {
  type: string;
  start_time: string;
  duration_days: number;
  times_per_day?: number;
  interval_days?: number;
  detail?: string;
  medicines: NurseTaskMedicineItemPayload[];
}

export interface NurseTaskBatchCreatePayload {
  plans: NurseTaskPlanPayload[];
}

export interface NurseTaskItem {
  task_id: number;
  type: string;
  time: string;
  hosp_id: number;
  status: string;
}

export type HistoryRange = "current" | "7d" | "30d";

export interface DoctorPatientRegistrationHistoryItem {
  reg_id: number;
  reg_date: string;
  visit_date?: string | null;
  status: string;
  reg_type: string;
  fee: number;
  doctor_id: number;
  patient_id: number;
  is_current: boolean;
  record?: {
    record_id: number;
    complaint?: string | null;
    diagnosis?: string | null;
    suggestion?: string | null;
  } | null;
}

export interface PrescriptionDetailItem {
  detail_id: number;
  medicine_id: number;
  medicine_name?: string | null;
  quantity: number;
  usage: string;
}

export interface PrescriptionItem {
  pres_id: number;
  create_time: string;
  total_amount?: number;
  status?: string;
  details: PrescriptionDetailItem[];
}

export interface ExaminationItem {
  exam_id: number;
  type: string;
  result?: string | null;
  date?: string | null;
}

export interface DoctorRegistrationDetail {
  registration: RegistrationItem;
  record?: {
    record_id: number;
    complaint: string;
    diagnosis: string;
    suggestion?: string | null;
  } | null;
  prescriptions: PrescriptionItem[];
  exams: ExaminationItem[];
  admissions?: unknown[];
}

export function fetchDoctorSchedule() {
  return http.get<RegistrationItem[]>("/api/doctor/schedule");
}

export function submitMedicalRecord(regId: number, payload: MedicalRecordPayload) {
  return http.post(`/api/doctor/consultations/${regId}`, payload);
}

export function fetchMedicalRecordByReg(regId: number) {
  return http.get(`/api/doctor/consultations/${regId}/record`);
}

export function startHandling(regId: number) {
  return http.post(`/api/doctor/consultations/${regId}/start`);
}

export function finishHandling(regId: number) {
  return http.post(`/api/doctor/consultations/${regId}/finish`);
}

export function fetchConsultationInfo(regId: number) {
  return http.get(`/api/doctor/consultations/${regId}/info`);
}

export function createExamination(regId: number, payload: { type: string }) {
  return http.post(`/api/doctor/consultations/${regId}/exams`, payload);
}

export function fetchExaminations(regId: number) {
  return http.get(`/api/doctor/consultations/${regId}/exams`);
}

export function fetchDoctorWards() {
  return http.get<WardInfo[]>("/api/doctor/wards");
}

export function fetchDoctorInpatients() {
  return http.get<DoctorInpatientItem[]>("/api/doctor/inpatients");
}

export function createNurseTasks(hospId: number, payload: NurseTaskBatchCreatePayload) {
  return http.post(`/api/doctor/hospitalizations/${hospId}/tasks`, payload);
}

export function hospitalizePatient(regId: number, payload: { ward_id: number; hosp_doctor_id?: number }) {
  return http.post(`/api/doctor/consultations/${regId}/hospitalize`, payload);
}

export function fetchDeptDoctors() {
  return http.get<DoctorBrief[]>("/api/doctor/dept/doctors");
}

export function exportTransferForm(regId: number) {
  return http.get(`/api/doctor/consultations/${regId}/transfer`, { responseType: "blob" });
}

export function fetchPatientRegistrationHistory(patientId: number, params: { range: HistoryRange; current_reg_id?: number }) {
  return http.get<DoctorPatientRegistrationHistoryItem[]>(`/api/doctor/patients/${patientId}/registrations/history`, { params });
}

export function fetchDoctorRegistrationDetail(regId: number) {
  return http.get<DoctorRegistrationDetail>(`/api/doctor/registrations/${regId}/detail`);
}
