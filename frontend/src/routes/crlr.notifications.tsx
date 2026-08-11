import { createFileRoute, Link } from "@tanstack/react-router";
import { Bell } from "lucide-react";
import { CRLRLayout } from "@/layouts/CRLRLayout";
import { PageHeader } from "@/components/common/PageHeader";
import { EmptyState, ErrorState, LoadingState } from "@/components/common/States";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { useAsyncData } from "@/hooks/useAsyncData";
import {
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead,
} from "@/services/notificationService";
import { cn } from "@/lib/utils";

export const Route = createFileRoute("/crlr/notifications")({
  head: () => ({
    meta: [
      { title: "Notifications — CR/LR Portal" },
      { name: "description", content: "Session notifications asking you to confirm whether the faculty is present." },
      { property: "og:title", content: "Notifications — CR/LR Portal" },
      { property: "og:description", content: "Faculty attendance confirmation requests for your section." },
    ],
  }),
  component: NotificationsPage,
});

function NotificationsPage() {
  const { data, loading, error, reload } = useAsyncData(() => getNotifications(), []);
  const notifications = data ?? [];
  const unread = notifications.filter((n) => !n.read).length;

  return (
    <CRLRLayout>
      <PageHeader
        title="Notifications"
        description={unread > 0 ? `${unread} unread` : "You are up to date"}
        actions={
          notifications.length > 0 ? (
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                await markAllNotificationsRead();
                reload();
              }}
            >
              Mark all as read
            </Button>
          ) : null
        }
      />

      {loading ? (
        <LoadingState rows={3} />
      ) : error ? (
        <ErrorState message={error} onRetry={reload} />
      ) : notifications.length === 0 ? (
        <EmptyState
          title="No notifications"
          description="Session notifications will appear here when a response is required."
          icon={Bell}
        />
      ) : (
        <div className="space-y-3">
          {notifications.map((n) => (
            <Card key={n.id} className={cn(!n.read && "border-primary/40 bg-accent/40")}>
              <CardContent className="space-y-3 p-4">
                <div className="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-3">
                  <div className="min-w-0">
                    <p className="truncate text-sm font-semibold">{n.title}</p>
                    <p className="truncate text-xs text-muted-foreground">
                      Section: {n.section} · {n.subject} · {n.time}
                    </p>
                  </div>
                  {!n.read ? (
                    <span className="rounded-full bg-primary px-2 py-0.5 text-xs font-medium text-primary-foreground">
                      New
                    </span>
                  ) : null}
                </div>
                <p className="text-sm">{n.message}</p>
                <div className="flex flex-wrap gap-2">
                  {n.sessionId ? (
                    <Button
                      asChild
                      size="sm"
                      onClick={async () => {
                        await markNotificationRead(n.id);
                      }}
                    >
                      <Link to="/crlr/attendance">Respond Now</Link>
                    </Button>
                  ) : null}
                  {!n.read ? (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={async () => {
                        await markNotificationRead(n.id);
                        reload();
                      }}
                    >
                      Mark as read
                    </Button>
                  ) : null}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </CRLRLayout>
  );
}
