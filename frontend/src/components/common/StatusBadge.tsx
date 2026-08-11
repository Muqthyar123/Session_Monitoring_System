import { cn } from "@/lib/utils";

type StatusKind =
  | "Upcoming"
  | "Active"
  | "Completed"
  | "Pending"
  | "Present"
  | "Not Present"
  | "Substitute"
  | "Processed"
  | "Processing"
  | "Failed"
  | "New"
  | "Acknowledged"
  | "Expired";

const styles: Record<StatusKind, string> = {
  Upcoming: "bg-secondary text-secondary-foreground",
  Active: "bg-info/12 text-info",
  Completed: "bg-secondary text-secondary-foreground",
  Pending: "bg-warning/20 text-warning-foreground",
  Present: "bg-success/12 text-success",
  "Not Present": "bg-destructive/12 text-destructive",
  Substitute: "bg-info/12 text-info",
  Processed: "bg-success/12 text-success",
  Processing: "bg-warning/20 text-warning-foreground",
  Failed: "bg-destructive/12 text-destructive",
  New: "bg-destructive/12 text-destructive",
  Acknowledged: "bg-secondary text-secondary-foreground",
  Expired: "bg-destructive/12 text-destructive",
};

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const tone = styles[status as StatusKind] ?? "bg-secondary text-secondary-foreground";
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap",
        tone,
        className,
      )}
    >
      {status}
    </span>
  );
}
