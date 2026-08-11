import { Link } from "@tanstack/react-router";
import { Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { useAsyncData } from "@/hooks/useAsyncData";
import { getNotifications } from "@/services/notificationService";

export function NotificationBell() {
  const { data } = useAsyncData(() => getNotifications(), []);
  const notifications = data ?? [];
  const unread = notifications.filter((n) => !n.read).length;

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon" className="relative" aria-label="Notifications">
          <Bell className="size-5" />
          {unread > 0 ? (
            <span className="absolute -right-0.5 -top-0.5 grid size-4 place-items-center rounded-full bg-destructive text-[10px] font-semibold text-destructive-foreground">
              {unread}
            </span>
          ) : null}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        <DropdownMenuLabel>Notifications</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {notifications.length === 0 ? (
          <p className="p-3 text-sm text-muted-foreground">No notifications.</p>
        ) : (
          notifications.slice(0, 4).map((n) => (
            <DropdownMenuItem key={n.id} className="flex flex-col items-start gap-0.5">
              <span className="text-sm font-medium">
                {n.title}
                {!n.read ? <span className="ml-2 text-xs text-primary">New</span> : null}
              </span>
              <span className="text-xs text-muted-foreground">
                {n.section} · {n.subject} · {n.time}
              </span>
            </DropdownMenuItem>
          ))
        )}
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link to="/crlr/notifications">View all notifications</Link>
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
