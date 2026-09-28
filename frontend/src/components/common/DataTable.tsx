import { useState, useEffect, type ReactNode } from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Button } from "@/components/ui/button";

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
  pageSize = 25,
  showPagination = true,
}: {
  columns: Column<T>[];
  rows?: T[];
  data?: T[];
  getRowId?: (row: T) => string;
  keyExtractor?: (row: T) => string;
  pageSize?: number;
  showPagination?: boolean;
}) {
  const tableRows = rows || data || [];
  const tableColumns = columns || [];
  const getKey = getRowId || keyExtractor || ((row: any, idx: number) => row?.id || row?._id || String(idx));

  const [currentPage, setCurrentPage] = useState(1);
  const totalRows = tableRows.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / pageSize));

  // Reset to page 1 whenever row count changes
  useEffect(() => {
    setCurrentPage(1);
  }, [tableRows.length]);

  const activePage = Math.min(currentPage, totalPages);
  const startIndex = (activePage - 1) * pageSize;
  const endIndex = Math.min(startIndex + pageSize, totalRows);
  const currentRows = showPagination ? tableRows.slice(startIndex, endIndex) : tableRows;

  return (
    <div className="w-full space-y-4">
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
            {currentRows.map((row, idx) => (
              <TableRow key={getKey(row, startIndex + idx)}>
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

      {showPagination && totalRows > 0 && (
        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between px-2 text-sm text-muted-foreground">
          <div>
            Showing {totalRows === 0 ? 0 : startIndex + 1}–{endIndex} of {totalRows}
          </div>
          <div className="flex items-center gap-1.5">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={activePage === 1}
              className="h-8 px-3 rounded-md border text-xs"
            >
              Previous
            </Button>
            <Button
              variant="default"
              size="sm"
              className="h-8 min-w-[32px] px-2.5 text-xs rounded-md bg-primary text-primary-foreground font-semibold cursor-default"
            >
              {activePage}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={activePage === totalPages}
              className="h-8 px-3 rounded-md border text-xs"
            >
              Next
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
