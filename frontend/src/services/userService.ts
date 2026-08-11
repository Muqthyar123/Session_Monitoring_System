import { mockDelay, downloadFile } from "./apiClient";
import { MOCK_CRLR_USERS, type CRLRUser } from "@/data/mock/mockData";

/** In-memory store so the demo UI behaves like a real CRUD screen. */
let store: CRLRUser[] = [...MOCK_CRLR_USERS];

export async function getCRLRUsers(): Promise<CRLRUser[]> {
  return mockDelay([...store]);
}

export async function createCRLRUser(data: Omit<CRLRUser, "id">): Promise<CRLRUser> {
  const user: CRLRUser = { ...data, id: `c-${Date.now()}` };
  store = [user, ...store];
  return mockDelay(user, 350);
}

export async function updateCRLRUser(id: string, data: Omit<CRLRUser, "id">): Promise<CRLRUser> {
  const updated: CRLRUser = { ...data, id };
  store = store.map((u) => (u.id === id ? updated : u));
  return mockDelay(updated, 350);
}

export async function deleteCRLRUser(id: string): Promise<void> {
  store = store.filter((u) => u.id !== id);
  return mockDelay(undefined, 300);
}

/** MOCK upload — real validation/parsing happens in the backend. */
export async function uploadCRLRExcel(file: File): Promise<{ message: string }> {
  if (!file.name.toLowerCase().endsWith(".xlsx")) {
    throw new Error("Please check the Excel format. Only .xlsx files are supported.");
  }
  return mockDelay({ message: "Upload successful" }, 1100);
}

export function downloadCRLRTemplate() {
  const header = "Name,Roll Number,Email,Role,Year,Section\n";
  const sample = "Aarav Menon,22CS2A01,aarav.menon@example.com,CR,2nd Year,II-A\n";
  downloadFile("CR_LR_Template.csv", header + sample);
}
