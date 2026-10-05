import { toast } from "sonner";

export interface ExportColumn<T = any> {
  key: keyof T | string;
  header: string;
  transform?: (val: any, row: T) => string | number | undefined | null;
}

/**
 * Cleanly escapes and formats a field for CSV / Excel export.
 */
function formatCSVField(val: any): string {
  if (val === null || val === undefined) {
    return '""';
  }
  const str = String(val).replace(/\r\n/g, " ").replace(/\n/g, " ").replace(/\r/g, " ");
  // Escape double quotes by doubling them
  const escaped = str.replace(/"/g, '""');
  return `"${escaped}"`;
}

/**
 * Universal CSV / Excel Export Function
 * Supports UTF-8 BOM so Microsoft Excel and Google Sheets render characters cleanly without corruptions.
 */
export function exportToCSV<T = any>(
  data: T[],
  filename: string,
  columns?: ExportColumn<T>[]
) {
  if (!data || data.length === 0) {
    toast.error("No data available to export.");
    return;
  }

  try {
    let headers: string[] = [];
    let keys: (keyof T | string)[] = [];
    let transformers: ((val: any, row: T) => any)[] = [];

    if (columns && columns.length > 0) {
      headers = columns.map((c) => c.header);
      keys = columns.map((c) => c.key);
      transformers = columns.map((c) => c.transform || ((v) => v));
    } else {
      // Auto-extract from first object
      const sample = data[0] as Record<string, any>;
      keys = Object.keys(sample).filter((k) => k !== "_id" && k !== "id");
      headers = keys.map((k) =>
        String(k)
          .replace(/_/g, " ")
          .replace(/([A-Z])/g, " $1")
          .replace(/^./, (str) => str.toUpperCase())
          .trim()
      );
      transformers = keys.map(() => (v: any) => v);
    }

    // Build CSV content
    const csvRows: string[] = [];

    // Header row
    csvRows.push(headers.map(formatCSVField).join(","));

    // Data rows
    for (const row of data) {
      const rowValues = keys.map((key, idx) => {
        const rawVal = (row as any)[key];
        const transformedVal = transformers[idx](rawVal, row);
        return formatCSVField(transformedVal);
      });
      csvRows.push(rowValues.join(","));
    }

    // UTF-8 BOM (\uFEFF) ensures Excel opens non-ASCII and formatted text correctly
    const csvContent = "\uFEFF" + csvRows.join("\r\n");
    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);

    const safeFilename = filename.endsWith(".csv") ? filename : `${filename}.csv`;
    const link = document.createElement("a");
    link.href = url;
    link.setAttribute("download", safeFilename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    toast.success(`Exported ${data.length} records to ${safeFilename}`);
  } catch (err: any) {
    console.error("Export error:", err);
    toast.error("Failed to export data.");
  }
}
