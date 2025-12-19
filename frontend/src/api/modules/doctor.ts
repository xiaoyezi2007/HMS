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

export function hospitalizePatient(regId: number, payload: { ward_id: number }) {
  return http.post(`/api/doctor/consultations/${regId}/hospitalize`, payload);
}

export function exportTransferForm(regId: number) {
  return http.get(`/api/doctor/consultations/${regId}/transfer`, { responseType: "blob" });
}
