import http from "../http";

export interface MedicineItem {
  medicine_id: number;
  name: string;
  price: number;
  stock: number;
  unit: string;
  expire_date: string;
}

export interface PrescriptionItemPayload {
  medicine_id: number;
  quantity: number;
  usage: string;
}

export interface PrescriptionPayload {
  record_id: number;
  items: PrescriptionItemPayload[];
}

export interface MedicinePurchasePayload {
  medicine_id: number;
  quantity: number;
}

export interface MedicineCreatePayload {
  name: string;
  price: number;
  stock: number;
  unit: string;
  expire_date: string;
}

export function fetchMedicines() {
  return http.get<MedicineItem[]>("/api/pharmacy/medicines");
}

export function createPrescription(payload: PrescriptionPayload) {
  return http.post("/api/pharmacy/prescriptions", payload);
}

export function fetchPrescriptionByRecord(recordId: number) {
  return http.get(`/api/pharmacy/prescriptions/by_record/${recordId}`);
}

export function purchaseMedicine(payload: MedicinePurchasePayload) {
  return http.post<MedicineItem>("/api/pharmacy/medicines/purchase", payload);
}

export function createMedicine(payload: MedicineCreatePayload) {
  return http.post<MedicineItem>("/api/pharmacy/medicines", payload);
}
