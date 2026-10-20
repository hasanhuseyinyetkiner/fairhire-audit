import { useQuery } from "@tanstack/react-query";
import { FileText, Moon, Scale, SlidersHorizontal, Sun, Table2, Upload } from "lucide-react";
import { type ReactNode, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router";

import { api } from "../api";
import type { Meta } from "../types";

const STEPS = [
  { key: "import", label: "Import", icon: Upload, suffix: "" },
  { key: "quality", label: "Model quality", icon: Table2, suffix: "/quality" },
  { key: "groups", label: "Group disparities", icon: Scale, suffix: "/groups" },
  { key: "threshold", label: "Threshold lab", icon: SlidersHorizontal, suffix: "/threshold" },
  { key: "report", label: "Audit report", icon: FileText, suffix: "/report" },
];

export function Shell() {
  const location = useLocation();
  const auditMatch = location.pathname.match(/^\/audits\/([^/]+)/);
  const auditId = auditMatch?.[1];
  const [dark, setDark] = useState(() => document.documentElement.classList.contains("dark"));
  const meta = useQuery({
    queryKey: ["meta"],
    queryFn: () => api<Meta>("/api/meta"),
  });

  function toggleTheme() {
    const next = !dark;
    document.documentElement.classList.toggle("dark", next);
    localStorage.setItem("fairhire-theme", next ? "dark" : "light");
    setDark(next);
  }

  return (
    <div className="min-h-screen lg:grid lg:grid-cols-[248px_minmax(0,1fr)]">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-md focus:bg-white focus:px-3 focus:py-2"
      >
        Skip to content
      </a>
      <aside className="flex flex-col bg-[#0b1220] text-slate-100 lg:min-h-screen">
        <div className="px-5 pb-4 pt-6">
          <div className="flex items-center gap-3">
            <span className="grid h-9 w-9 place-items-center rounded-xl bg-[#2563EB] text-sm font-bold">F</span>
            <div>
              <p className="text-sm font-semibold tracking-tight">FairHire Audit</p>
              <p className="text-xs text-slate-400">Evidence, not a verdict</p>
            </div>
          </div>
        </div>
        <nav aria-label="Audit sections" className="flex gap-1 overflow-x-auto px-3 pb-4 lg:flex-col">
          {STEPS.map((step, index) => {
            const enabled = step.key === "import" || Boolean(auditId);
            const to = step.key === "import" ? "/" : `/audits/${auditId}${step.suffix}`;
            const icon = <step.icon size={16} aria-hidden="true" />;
            const inner = (
              <>
                <span className="w-5 text-[11px] text-slate-500">{String(index + 1).padStart(2, "0")}</span>
                {icon}
                <span>{step.label}</span>
              </>
            );
            if (!enabled) {
              return (
                <span
                  key={step.key}
                  className="flex items-center gap-2 rounded-xl px-3 py-2 text-sm text-slate-500"
                  aria-disabled="true"
                >
                  {inner}
                </span>
              );
            }
            return (
              <NavLink
                key={step.key}
                to={to}
                end={step.key === "import"}
                className={({ isActive }) =>
                  `flex items-center gap-2 rounded-xl px-3 py-2 text-sm ${
                    isActive ? "bg-white/10 text-white" : "text-slate-300 hover:bg-white/5"
                  }`
                }
              >
                {inner}
              </NavLink>
            );
          })}
        </nav>
        <div className="mt-auto px-4 py-4">
          <button
            type="button"
            onClick={toggleTheme}
            className="flex w-full items-center justify-center gap-2 rounded-xl border border-white/10 px-3 py-2 text-sm"
            aria-pressed={dark}
            data-testid="theme-toggle"
          >
            {dark ? <Sun size={16} aria-hidden="true" /> : <Moon size={16} aria-hidden="true" />}
            {dark ? "Light theme" : "Dark theme"}
          </button>
        </div>
      </aside>
      <div className="min-w-0">
        {meta.data?.banner ? (
          <div className="bg-[#2563EB] px-4 py-2 text-center text-sm font-medium text-white" data-testid="demo-banner">
            {meta.data.banner}
          </div>
        ) : null}
        <main id="main" className="mx-auto max-w-6xl px-4 py-6 sm:px-6 lg:px-8">
          <Outlet />
        </main>
      </div>
    </div>
  );
}

export function PageIntro({
  eyebrow,
  title,
  lede,
}: {
  eyebrow: string;
  title: string;
  lede: ReactNode;
}) {
  return (
    <header className="mb-6 max-w-3xl">
      <p className="text-xs font-semibold uppercase tracking-[0.16em] text-[#2563EB]">{eyebrow}</p>
      <h1 className="mt-2 text-3xl font-semibold tracking-tight">{title}</h1>
      <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{lede}</p>
    </header>
  );
}
