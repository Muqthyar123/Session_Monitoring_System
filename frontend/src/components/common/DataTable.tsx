import type { ReactNode } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

export interface Column<T> {
  key: string;
  header: string;
  cell?: (row: T) => ReactNode;
  className?: string;
}

export function DataTable<T>({
  columns,
  rows,
  data,
  getRowId,
  keyExtractor,
}: {
  columns: Column<T>[];
  rows?: T[];
  data?: T[];
  getRowId?: (row: T) => string;
  keyExtractor?: (row: T) => string;
}) {
  const tableRows = rows || data || [];
  const tableColumns = columns || [];
  const getKey = getRowId || keyExtractor || ((row: any, idx: number) => row?.id || row?._id || String(idx));

  return (
    <div className="w-full overflow-x-auto rounded-lg border border-border bg-card">
      <Table>
        <TableHeader>
          <TableRow>
            {tableColumns.map((col) => (
              <TableHead key={col.key} className={col.className}>
                {col.header}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>
        <TableBody>
          {tableRows.map((row, idx) => (
            <TableRow key={getKey(row, idx)}>
              {tableColumns.map((col) => (
                <TableCell key={col.key} className={col.className}>
                  {col.cell ? col.cell(row) : ((row as any)?.[col.key] ?? null)}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
