import type { AdminAlert } from "@/data/mock/mockData";

const columns = ["Notification ID", "Title", "Message", "Type", "Section", "Subject", "Session", "Reported By", "Status", "Created At"];

function rowsFor(alerts: AdminAlert[]) {
  return alerts.map((alert) => {
    const reason = alert.reason || "";
    const type = reason.toLowerCase().includes("response") ? "NO_RESPONSE_ALERT" : "FACULTY_ABSENT_ALERT";
    return [
      alert.id,
      type === "NO_RESPONSE_ALERT" ? "No attendance response" : "Faculty attendance alert",
      reason,
      type,
      alert.section,
      alert.subject,
      alert.session,
      alert.reportedBy,
      alert.status || "New",
      alert.created_at ? new Date(alert.created_at).toLocaleString("en-IN", { timeZone: "Asia/Kolkata" }) : alert.time,
    ].map((value) => String(value ?? ""));
  });
}

function saveBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function exportCsv(data: string[][], filename: string) {
  const csv = [columns, ...data].map((row) => row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(",")).join("\r\n");
  saveBlob(new Blob(["\uFEFF", csv], { type: "text/csv;charset=utf-8" }), filename);
}

const xml = (value: string) => value.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;").replace(/'/g, "&apos;");
const utf8 = (value: string) => new TextEncoder().encode(value);

function crc32(bytes: Uint8Array) {
  let crc = 0xffffffff;
  for (const byte of bytes) {
    crc ^= byte;
    for (let bit = 0; bit < 8; bit++) crc = (crc >>> 1) ^ (crc & 1 ? 0xedb88320 : 0);
  }
  return (crc ^ 0xffffffff) >>> 0;
}

function zipStored(files: Array<{ name: string; content: string }>) {
  const locals: Uint8Array[] = [];
  const centrals: Uint8Array[] = [];
  let offset = 0;
  const put16 = (view: DataView, position: number, value: number) => view.setUint16(position, value, true);
  const put32 = (view: DataView, position: number, value: number) => view.setUint32(position, value, true);
  for (const file of files) {
    const name = utf8(file.name);
    const content = utf8(file.content);
    const crc = crc32(content);
    const local = new Uint8Array(30 + name.length + content.length);
    const lv = new DataView(local.buffer);
    put32(lv, 0, 0x04034b50); put16(lv, 4, 20); put16(lv, 6, 0x0800); put16(lv, 8, 0);
    put32(lv, 14, crc); put32(lv, 18, content.length); put32(lv, 22, content.length); put16(lv, 26, name.length); put16(lv, 28, 0);
    local.set(name, 30); local.set(content, 30 + name.length); locals.push(local);

    const central = new Uint8Array(46 + name.length);
    const cv = new DataView(central.buffer);
    put32(cv, 0, 0x02014b50); put16(cv, 4, 20); put16(cv, 6, 20); put16(cv, 8, 0x0800); put16(cv, 10, 0);
    put32(cv, 16, crc); put32(cv, 20, content.length); put32(cv, 24, content.length); put16(cv, 28, name.length); put16(cv, 30, 0); put16(cv, 32, 0); put16(cv, 34, 0); put16(cv, 36, 0); put32(cv, 38, 0); put32(cv, 42, offset);
    central.set(name, 46); centrals.push(central); offset += local.length;
  }
  const centralSize = centrals.reduce((sum, item) => sum + item.length, 0);
  const end = new Uint8Array(22); const ev = new DataView(end.buffer);
  put32(ev, 0, 0x06054b50); put16(ev, 8, files.length); put16(ev, 10, files.length); put32(ev, 12, centralSize); put32(ev, 16, offset);
  return new Blob([...locals, ...centrals, end] as unknown as BlobPart[], { type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" });
}

function exportXlsx(data: string[][], filename: string) {
  const allRows = [columns, ...data];
  const sheetRows = allRows.map((row, rowIndex) => `<row r="${rowIndex + 1}">${row.map((value, colIndex) => {
    let col = ""; let n = colIndex + 1;
    while (n) { const rem = (n - 1) % 26; col = String.fromCharCode(65 + rem) + col; n = Math.floor((n - 1) / 26); }
    return `<c r="${col}${rowIndex + 1}" t="inlineStr"><is><t xml:space="preserve">${xml(value)}</t></is></c>`;
  }).join("")}</row>`).join("");
  const sheet = `<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>${sheetRows}</sheetData></worksheet>`;
  const blob = zipStored([
    { name: "[Content_Types].xml", content: `<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="xml" ContentType="application/xml"/><Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/><Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/></Types>` },
    { name: "_rels/.rels", content: `<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>` },
    { name: "xl/workbook.xml", content: `<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Notifications" sheetId="1" r:id="rId1"/></sheets></workbook>` },
    { name: "xl/_rels/workbook.xml.rels", content: `<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>` },
    { name: "xl/worksheets/sheet1.xml", content: sheet },
  ]);
  saveBlob(blob, filename);
}

function pdfEscape(value: string) {
  return value.normalize("NFKD").replace(/[\u0300-\u036f]/g, "").replace(/[^\x20-\x7E]/g, "?").replace(/([\\()])/g, "\\$1");
}

function exportPdf(data: string[][], filename: string) {
  const lines = ["Notification History", `Generated ${new Date().toLocaleString("en-IN", { timeZone: "Asia/Kolkata" })} Asia/Kolkata`, "", ...data.map((row) => `${row[9]} | ${row[1]} | ${row[4]} | ${row[5]} | ${row[6]} | ${row[2]}`)];
  const wrapped = lines.flatMap((line) => line.length > 105 ? Array.from({ length: Math.ceil(line.length / 105) }, (_, index) => line.slice(index * 105, (index + 1) * 105)) : [line]);
  const pages: string[][] = [];
  for (let i = 0; i < wrapped.length; i += 54) pages.push(wrapped.slice(i, i + 54));
  const objects: string[] = ["", "<< /Type /Catalog /Pages 2 0 R >>", "", "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"];
  const pageRefs: string[] = [];
  pages.forEach((pageLines) => {
    const pageId = objects.length; const streamId = pageId + 1; pageRefs.push(`${pageId} 0 R`);
    const text = pageLines.map((line, index) => `(${pdfEscape(line)}) Tj${index < pageLines.length - 1 ? " T*" : ""}`).join("\n");
    const stream = `BT /F1 8 Tf 40 755 Td 11 TL\n${text}\nET`;
    objects.push(`<< /Type /Page /Parent 2 0 R /MediaBox [0 0 842 792] /Resources << /Font << /F1 3 0 R >> >> /Contents ${streamId} 0 R >>`);
    objects.push(`<< /Length ${utf8(stream).length} >>\nstream\n${stream}\nendstream`);
  });
  objects[2] = `<< /Type /Pages /Kids [${pageRefs.join(" ")}] /Count ${pageRefs.length} >>`;
  let pdf = "%PDF-1.4\n"; const offsets = [0];
  objects.slice(1).forEach((object, index) => { offsets.push(utf8(pdf).length); pdf += `${index + 1} 0 obj\n${object}\nendobj\n`; });
  const xrefOffset = utf8(pdf).length; pdf += `xref\n0 ${objects.length}\n0000000000 65535 f \n`;
  for (const offset of offsets.slice(1)) pdf += `${String(offset).padStart(10, "0")} 00000 n \n`;
  pdf += `trailer\n<< /Size ${objects.length} /Root 1 0 R >>\nstartxref\n${xrefOffset}\n%%EOF`;
  saveBlob(new Blob([pdf], { type: "application/pdf" }), filename);
}

export function downloadNotificationExport(alerts: AdminAlert[], format: "pdf" | "xlsx" | "csv") {
  const data = rowsFor(alerts);
  const filename = `Notification_History.${format}`;
  if (format === "csv") exportCsv(data, filename);
  else if (format === "xlsx") exportXlsx(data, filename);
  else exportPdf(data, filename);
}
