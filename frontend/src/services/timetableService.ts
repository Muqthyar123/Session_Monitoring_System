import { mockDelay, downloadFile } from "./apiClient";
import {
  MOCK_TIMETABLE_UPLOADS,
  buildMockTimetable,
  type TimetablePeriod,
  type TimetableUpload,
} from "@/data/mock/mockData";

export async function getTimetableUploads(): Promise<TimetableUpload[]> {
  return mockDelay(MOCK_TIMETABLE_UPLOADS);
}

export async function getTimetable(year: string, section: string): Promise<TimetablePeriod[]> {
  return mockDelay(buildMockTimetable(year, section), 500);
}

/**
 * MOCK upload. The frontend does not parse the workbook — the Python backend
 * will parse `All_Class_Timetables_Format.xlsx` later.
 */
export async function uploadTimetable(file: File): Promise<{ message: string }> {
  if (!file.name.toLowerCase().endsWith(".xlsx")) {
    throw new Error("Please check the Excel format. Only .xlsx files are supported.");
  }
  return mockDelay({ message: "Upload successful" }, 1200);
}

export function downloadTimetableTemplate() {
  const header = "Day,Period,Start Time,End Time,Subject,Room\n";
  const sample =
    "Monday,1,09:10,10:00,Database Management Systems,B-204\n" +
    "Monday,2,10:00,10:50,Operating Systems,B-205\n";
  downloadFile("Timetable_Template.csv", header + sample);
}
