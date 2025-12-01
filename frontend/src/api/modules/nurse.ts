import http from "../http";

export interface NurseScheduleItem {
  schedule_id: number;
  nurse_name: string;
  ward_type: string;
  start_time: string;
  end_time: string;
}

export interface NurseProfile {
  nurse_id: number;
  name: string;
  is_head_nurse: boolean;
}

export interface WardScheduleEntry {
  schedule_id: number;
  nurse_id: number;
  nurse_name: string;
  start_time: string;
  end_time: string;
}

export interface WardScheduleGroup {
  ward_id: number;
  ward_type: string;
  schedules: WardScheduleEntry[];
}

export interface NurseOption {
  nurse_id: number;
  name: string;
  is_head_nurse: boolean;
}

export interface HeadScheduleContext {
  wards: WardScheduleGroup[];
  nurses: NurseOption[];
}

export interface ScheduleUpsertPayload {
  ward_id: number;
  start_time: string;
  end_time: string;
  nurse_ids: number[];
  source_ward_id?: number;
  source_start_time?: string;
  source_end_time?: string;
}

export interface AutoSchedulePayload {
  start_time?: string;
  shift_hours?: number;
  shift_count?: number;
  ward_ids?: number[];
}

export interface InpatientItem {
  hosp_id: number;
  patient_id: number;
  patient_name: string;
  ward_type: string;
  in_date: string;
  stay_hours: number;
}

export interface DischargeResponse {
  detail: string;
  bill_amount: number;
  stay_hours: number;
  payment_id: number;
}

export function fetchMySchedules() {
  return http.get<NurseScheduleItem[]>("/api/nurse/my_schedules");
}

export function fetchNurseProfile() {
  return http.get<NurseProfile>("/api/nurse/profile");
}

export function fetchHeadScheduleContext() {
  return http.get<HeadScheduleContext>("/api/nurse/head/context");
}

export function upsertWardSchedule(payload: ScheduleUpsertPayload) {
  return http.post("/api/nurse/head/schedules/upsert", payload);
}

export function deleteScheduleSlot(scheduleId: number) {
  return http.delete(`/api/nurse/head/schedules/${scheduleId}`);
}

export function autoArrangeSchedules(payload: AutoSchedulePayload) {
  return http.post("/api/nurse/head/schedules/auto", payload);
}

export function fetchHeadInpatients() {
  return http.get<InpatientItem[]>("/api/nurse/head/inpatients");
}

export function dischargeInpatient(hospId: number) {
  return http.post<DischargeResponse>(`/api/nurse/head/hospitalizations/${hospId}/discharge`);
}
