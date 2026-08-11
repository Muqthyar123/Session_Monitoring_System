import { useEffect, useState } from "react";
import { Timer } from "lucide-react";
import type { ClassSession } from "@/data/mock/mockData";

function format(seconds: number) {
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
}

/**
 * Displays the remaining response window reported by the backend.
 * The frontend never decides that the window expired, and never raises alerts —
 * `responseWindowExpired` always comes from the backend.
 */
export function ResponseWindow({ session }: { session: ClassSession }) {
  const initial = session.responseWindowSecondsRemaining;
  const [remaining, setRemaining] = useState<number | null>(initial);

  useEffect(() => {
    setRemaining(initial);
  }, [initial]);

  useEffect(() => {
    if (remaining === null || remaining <= 0) return;
    const id = setInterval(() => setRemaining((v) => (v === null ? v : Math.max(0, v - 1))), 1000);
    return () => clearInterval(id);
  }, [remaining]);

  if (session.responseWindowExpired) {
    return (
      <p className="flex items-center gap-2 rounded-md bg-destructive/10 px-3 py-2 text-sm font-medium text-destructive">
        <Timer className="size-4" /> Response window expired
      </p>
    );
  }

  if (remaining === null) return null;

  return (
    <p className="flex items-center gap-2 rounded-md bg-warning/15 px-3 py-2 text-sm font-medium text-warning-foreground">
      <Timer className="size-4" /> Response required — time remaining: {format(remaining)}
    </p>
  );
}
