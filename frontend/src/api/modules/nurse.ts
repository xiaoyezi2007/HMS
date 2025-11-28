import http from "../http";

export interface NurseScheduleItem {
  schedule_id: number;
  nurse_name: string;
  ward_type: string;
  time: string;
}

export function fetchMySchedules() {
  return http.get<NurseScheduleItem[]>("/api/nurse/my_schedules");
}
