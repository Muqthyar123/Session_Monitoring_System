import { createFileRoute, Link } from "@tanstack/react-router";
import {
  GraduationCap,
  ShieldCheck,
  Users,
  ArrowRight,
  CheckCircle2,
  CalendarCheck2,
  BellRing,
  Activity,
} from "lucide-react";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "Attendance Management System — Select Portal" },
      {
        name: "description",
        content:
          "Smart attendance monitoring system for academic sessions with Admin, Mentor, and CR/LR portals.",
      },
    ],
  }),
  component: LandingPage,
});

function LandingPage() {
  return (
    <div className="flex min-h-screen w-full items-center justify-center bg-slate-100 p-4 sm:p-6 lg:p-10 dark:bg-slate-950">
      <div className="w-full max-w-5xl overflow-hidden rounded-3xl border border-slate-200/80 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-900 grid grid-cols-1 lg:grid-cols-12 min-h-[640px]">
        
        {/* ============================================================ */}
        {/* LEFT SIDE: Brand, Features & Visual Illustration             */}
        {/* ============================================================ */}
        <div className="relative flex flex-col justify-between overflow-hidden bg-gradient-to-br from-indigo-950 via-slate-900 to-slate-950 p-8 sm:p-10 text-white lg:col-span-5">
          {/* Ambient Glows */}
          <div className="absolute -left-20 -top-20 h-64 w-64 rounded-full bg-indigo-500/20 blur-3xl pointer-events-none" />
          <div className="absolute -bottom-20 -right-20 h-64 w-64 rounded-full bg-emerald-500/15 blur-3xl pointer-events-none" />

          {/* Top: Icon & Title */}
          <div className="relative z-10 space-y-4">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-white/10 backdrop-blur-md border border-white/15 shadow-inner">
              <GraduationCap className="h-8 w-8 text-indigo-300" />
            </div>

            <div className="space-y-1">
              <h2 className="text-xs font-bold tracking-widest text-indigo-400 uppercase">
                ATTENDANCE
              </h2>
              <h1 className="text-2xl font-black tracking-tight text-white sm:text-3xl">
                MANAGEMENT SYSTEM
              </h1>
            </div>

            <p className="text-sm font-medium text-slate-300 leading-relaxed max-w-sm">
              Smart attendance monitoring for academic sessions
            </p>
          </div>

          {/* Middle: Feature Checklist */}
          <div className="relative z-10 my-8 space-y-3">
            {[
              "Timetable-driven sessions",
              "Faculty attendance",
              "Student monitoring",
              "Absence alerts",
            ].map((feature) => (
              <div key={feature} className="flex items-center gap-3 text-sm text-slate-200 font-medium">
                <div className="flex h-5 w-5 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-400 shrink-0">
                  <CheckCircle2 className="h-3.5 w-3.5" />
                </div>
                <span>{feature}</span>
              </div>
            ))}
          </div>

          {/* Bottom: Illustration / Status Widget */}
          <div className="relative z-10 rounded-2xl border border-white/10 bg-white/5 p-4 backdrop-blur-md space-y-2.5">
            <div className="flex items-center justify-between text-xs font-semibold text-indigo-300">
              <span className="flex items-center gap-1.5">
                <Activity className="size-3.5 text-emerald-400 animate-pulse" /> Live Monitoring
              </span>
              <span className="text-[11px] text-slate-400">Campus Cloud</span>
            </div>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="rounded-lg bg-black/20 p-2 border border-white/5">
                <p className="text-slate-400">Daily Sessions</p>
                <p className="font-bold text-white text-sm">Automated</p>
              </div>
              <div className="rounded-lg bg-black/20 p-2 border border-white/5">
                <p className="text-slate-400">Real-Time Sync</p>
                <p className="font-bold text-emerald-400 text-sm">Active</p>
              </div>
            </div>
          </div>
        </div>

        {/* ============================================================ */}
        {/* RIGHT SIDE: Portal Select Cards                              */}
        {/* ============================================================ */}
        <div className="flex flex-col justify-between p-8 sm:p-12 lg:col-span-7 bg-white dark:bg-slate-900">
          <div className="space-y-6">
            {/* Header */}
            <div>
              <span className="inline-block text-xs font-semibold uppercase tracking-wider text-indigo-600 dark:text-indigo-400 mb-1">
                Welcome back
              </span>
              <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white sm:text-3xl">
                Select your portal
              </h2>
              <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
                Choose how you want to continue
              </p>
            </div>

            {/* Portal Action Cards */}
            <div className="space-y-3.5">
              {/* 1. Admin Portal */}
              <Link
                to="/admin/login"
                className="group flex items-center justify-between p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 hover:bg-indigo-50/60 dark:hover:bg-indigo-950/30 hover:border-indigo-500/40 transition-all duration-200 hover:shadow-md cursor-pointer"
              >
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-indigo-100 dark:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400 group-hover:bg-indigo-600 group-hover:text-white transition-colors duration-200">
                    <ShieldCheck className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="font-bold text-base text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                      Admin Portal
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Manage system &amp; timetable
                    </p>
                  </div>
                </div>
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-200/60 dark:bg-slate-700/60 text-slate-600 dark:text-slate-300 group-hover:bg-indigo-600 group-hover:text-white transition-all duration-200 group-hover:translate-x-1">
                  <ArrowRight className="h-4 w-4" />
                </div>
              </Link>

              {/* 2. Mentor Portal */}
              <Link
                to="/mentor/login"
                className="group flex items-center justify-between p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 hover:bg-emerald-50/60 dark:hover:bg-emerald-950/30 hover:border-emerald-500/40 transition-all duration-200 hover:shadow-md cursor-pointer"
              >
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-100 dark:bg-emerald-900/50 text-emerald-600 dark:text-emerald-400 group-hover:bg-emerald-600 group-hover:text-white transition-colors duration-200">
                    <GraduationCap className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="font-bold text-base text-slate-900 dark:text-white group-hover:text-emerald-600 dark:group-hover:text-emerald-400 transition-colors">
                      Mentor Portal
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Monitor students &amp; absence
                    </p>
                  </div>
                </div>
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-200/60 dark:bg-slate-700/60 text-slate-600 dark:text-slate-300 group-hover:bg-emerald-600 group-hover:text-white transition-all duration-200 group-hover:translate-x-1">
                  <ArrowRight className="h-4 w-4" />
                </div>
              </Link>

              {/* 3. CR / LR Portal */}
              <Link
                to="/auth/login"
                className="group flex items-center justify-between p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 hover:bg-blue-50/60 dark:hover:bg-blue-950/30 hover:border-blue-500/40 transition-all duration-200 hover:shadow-md cursor-pointer"
              >
                <div className="flex items-center gap-4">
                  <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-blue-100 dark:bg-blue-900/50 text-blue-600 dark:text-blue-400 group-hover:bg-blue-600 group-hover:text-white transition-colors duration-200">
                    <Users className="h-6 w-6" />
                  </div>
                  <div>
                    <h3 className="font-bold text-base text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">
                      CR / LR Portal
                    </h3>
                    <p className="text-xs text-slate-500 dark:text-slate-400">
                      Manage class attendance
                    </p>
                  </div>
                </div>
                <div className="flex h-9 w-9 items-center justify-center rounded-full bg-slate-200/60 dark:bg-slate-700/60 text-slate-600 dark:text-slate-300 group-hover:bg-blue-600 group-hover:text-white transition-all duration-200 group-hover:translate-x-1">
                  <ArrowRight className="h-4 w-4" />
                </div>
              </Link>
            </div>
          </div>

          {/* Footer Note */}
          <div className="pt-6 border-t border-slate-100 dark:border-slate-800 text-center">
            <p className="text-xs text-slate-400">
              College Faculty &amp; Student Attendance Session Monitoring System
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
