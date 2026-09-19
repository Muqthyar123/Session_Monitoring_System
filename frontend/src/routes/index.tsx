import { createFileRoute, Link } from "@tanstack/react-router";
import { GraduationCap, ShieldCheck, Users } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Faculty Attendance & Session Monitoring System" },
      {
        name: "description",
        content:
          "College system to monitor faculty attendance for scheduled class sessions, with admin and CR/LR portals.",
      },
      { property: "og:title", content: "Faculty Attendance & Session Monitoring System" },
      {
        property: "og:description",
        content: "Monitor faculty attendance for scheduled class sessions across sections.",
      },
    ],
  }),
  component: Landing,
});

function Landing() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 bg-background px-4 py-12">
      <div className="flex flex-col items-center gap-3 text-center">
        <span className="grid size-14 place-items-center rounded-xl bg-primary text-primary-foreground">
          <GraduationCap className="size-7" />
        </span>
        <h1 className="text-2xl font-semibold tracking-tight sm:text-3xl">
          Faculty Attendance &amp; Session Monitoring System
        </h1>
        <p className="max-w-xl text-sm text-muted-foreground">
          Timetable-driven monitoring of faculty attendance for scheduled class sessions.
          Choose your portal to continue.
        </p>
      </div>

      <div className="grid w-full max-w-3xl gap-4 sm:grid-cols-2">
        <Card>
          <CardHeader>
            <ShieldCheck className="size-6 text-primary" />
            <CardTitle className="text-lg">Admin Login</CardTitle>
            <CardDescription>
              Manage timetables, CR/LR records, sessions and attendance alerts.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild className="w-full">
              <Link to="/admin/login">Continue as Admin</Link>
            </Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <Users className="size-6 text-primary" />
            <CardTitle className="text-lg">CR / LR Login</CardTitle>
            <CardDescription>
              Respond to faculty attendance requests for your assigned section.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button asChild variant="outline" className="w-full">
              <Link to="/auth/login">Continue as CR / LR</Link>
            </Button>
          </CardContent>
        </Card>
      </div>

      <p className="text-xs text-muted-foreground text-center">
        Production System — Connected to Live FastAPI Backend &amp; MongoDB Database.
      </p>
    </div>
  );
}
