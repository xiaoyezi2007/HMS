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

export interface WardOverviewItem {
  ward_id: number;
  ward_type: string;
  bed_count: number;
}

export interface WardRecordItem {
  ward_id: number;
  ward_type: string;
  hosp_id: number;
  record_id: number;
  patient_id: number;
  patient_name: string;
  complaint: string;
  diagnosis: string;
  suggestion?: string;
  in_date: string;
}

export interface WardTaskItem {
  task_id: number;
  hosp_id: number;
  patient_name: string;
  type: string;
  time: string;
  status: string;
  nurse_name: string;
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

export interface TodayTaskItem {
  task_id: number;
  patient_name: string;
  type: string;
  time: string;
  status: string;
  nurse_name: string;
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

export function fetchWardOverview() {
  return http.get<WardOverviewItem[]>("/api/nurse/ward_overview");
}

export function fetchWardRecords(wardId: number) {
  return http.get<WardRecordItem[]>(`/api/nurse/ward/${wardId}/records`);
}

export function fetchWardTasks(wardId: number) {
  return http.get<WardTaskItem[]>(`/api/nurse/ward/${wardId}/tasks`);
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

export function fetchTodayTasks() {
  return http.get<TodayTaskItem[]>("/api/nurse/today_tasks");
}

export function completeTask(taskId: number) {
  return http.post(`/api/nurse/tasks/${taskId}/complete`);
}
