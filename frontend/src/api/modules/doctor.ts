import http from "../http";

export interface RegistrationItem {
  reg_id: number;
  reg_date: string;
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
