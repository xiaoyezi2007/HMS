import http from "../http";

export interface PatientProfile {
  name: string;
  gender: string;
  birth_date: string;
  id_number: string;
  address: string;
}

export interface PatientProfileResponse extends PatientProfile {
  patient_id: number;
  phone: string;
}

export interface Department {
  dept_id: number;
  dept_name: string;
  telephone?: string;
}

export interface DoctorItem {
  doctor_id: number;
  name: string;
  title: string;
  gender: string;
}

export interface RegistrationPayload {
  doctor_id: number;
  reg_type: string;
}

export interface RegistrationItem {
  reg_id: number;
  reg_date: string;
  reg_type: string;
  fee: number;
  status: string;
  patient_id: number;
  doctor_id: number;
}

export function createPatientProfile(payload: PatientProfile) {
  return http.post("/api/profile", payload);
}

export function fetchPatientProfile() {
  return http.get<PatientProfileResponse>("/api/profile");
}

export function fetchDepartments() {
  return http.get<Department[]>("/api/departments");
}

export function fetchDoctors(deptId: number) {
  return http.get<DoctorItem[]>(`/api/doctors/${deptId}`);
}

export function fetchDoctorById(doctorId: number) {
  return http.get<DoctorItem>(`/api/doctors/id/${doctorId}`);
}

export function createRegistration(payload: RegistrationPayload) {
  return http.post("/api/registrations", payload);
}

export function fetchMyRegistrations() {
  return http.get<RegistrationItem[]>("/api/registrations");
}

export interface MedicalRecordItem {
  record_id: number;
  create_time: string;
  complaint: string;
  diagnosis: string;
  suggestion?: string | null;
  reg_id: number;
}

export function fetchMyMedicalRecords() {
  return http.get<MedicalRecordItem[]>(`/api/medical_records`);
}

export function fetchPatientMedicalRecords(patientId: number) {
  return http.get<MedicalRecordItem[]>(`/api/patients/${patientId}/medical_records`);
}

export function fetchPatientById(patientId: number) {
  return http.get<PatientProfileResponse>(`/api/patients/${patientId}`);
}

export function fetchRegistrationDetail(regId: number) {
  return http.get(`/api/registrations/${regId}/detail`);
}

export function fetchPatientExaminations() {
  return http.get(`/api/examinations`);
}

export interface PaymentItem {
  payment_id: number;
  type: string;
  amount: number;
  time: string;
  patient_id: number;
  pres_id?: number | null;
  exam_id?: number | null;
  hosp_id?: number | null;
  status: string;
  exam_info?: {
    exam_id: number;
    type: string;
    result?: string;
    date?: string;
  } | null;
  prescription_info?: {
    pres_id?: number;
    total_amount?: number;
    details: Array<{
      medicine_id: number;
      medicine_name?: string | null;
      quantity: number;
      usage: string;
    }>;
  } | null;
  hospitalization_info?: {
    hosp_id: number;
    ward_id?: number | null;
    ward_type?: string | null;
    status: string;
    in_date: string;
    out_date?: string | null;
    duration_hours: number;
    duration_days: number;
  } | null;
}

export function fetchMyPayments() {
  return http.get<PaymentItem[]>(`/api/payments`);
}

export function payPayment(paymentId: number) {
  return http.post(`/api/payments/${paymentId}/pay`);
}
