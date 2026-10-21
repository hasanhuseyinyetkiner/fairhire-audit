import { Info } from "lucide-react";
import type { HTMLAttributes, ReactNode } from "react";

import { formatCount, formatInterval, formatRate } from "../lib/format";
import type { ConfidenceInterval, Metric } from "../types";

export function Panel({
  children,
  className = "",
  ...rest
}: { children: ReactNode; className?: string } & HTMLAttributes<HTMLElement>) {
  return (
    <section
      className={`rounded-2xl border border-slate-200/80 bg-white p-5 shadow-[0_1px_2px_rgba(15,23,42,0.04)] dark:border-white/10 dark:bg-[#121826] ${className}`}
      {...rest}
    >
      {children}
    </section>
  );
}

export function Loading({ label }: { label: string }) {
  return (
    <div role="status" className="space-y-3" aria-live="polite">
      <p className="text-sm text-slate-500">{label}</p>
      <div className="h-24 animate-pulse rounded-2xl bg-slate-200/80 dark:bg-white/5" />
      <div className="h-40 animate-pulse rounded-2xl bg-slate-200/60 dark:bg-white/5" />
    </div>
  );
}

export function ErrorNote({ message }: { message: string }) {
  return (
    <div role="alert" className="rounded-2xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-800 dark:border-rose-900 dark:bg-rose-950/40 dark:text-rose-100">
      {message}
    </div>
  );
}

export function EmptyNote({ title, body }: { title: string; body: string }) {
  return (
    <Panel>
      <h2 className="text-lg font-semibold">{title}</h2>
      <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{body}</p>
    </Panel>
  );
}

export function FormulaTip({ formula }: { formula: string }) {
  return (
    <span className="group relative inline-flex">
      <button
        type="button"
        className="rounded-full p-1 text-slate-400 hover:text-[#2563EB]"
        aria-label={`Formula: ${formula}`}
      >
        <Info size={14} aria-hidden="true" />
      </button>
      <span className="pointer-events-none absolute left-0 top-7 z-20 hidden w-64 rounded-lg border border-slate-200 bg-white p-2 text-left text-xs leading-5 text-slate-700 shadow-lg group-focus-within:block group-hover:block dark:border-white/10 dark:bg-[#0f172a] dark:text-slate-200">
        {formula}
      </span>
    </span>
  );
}

export function RateReadout({ metric }: { metric: Metric }) {
  return (
    <div className="min-w-0">
      <div className="flex items-center gap-1">
        <span className="truncate text-sm text-slate-600 dark:text-slate-300">{metric.label}</span>
        <FormulaTip formula={metric.formula} />
      </div>
      <div className="tabular text-xl font-semibold tracking-tight">{formatRate(metric.value)}</div>
      <div className="tabular text-xs text-slate-500">
        {metric.numerator === null || metric.denominator === null
          ? "n in the rate is withheld"
          : `${formatCount(metric.numerator)} / ${formatCount(metric.denominator)}`}
        {metric.sample_size !== null ? ` · group n=${formatCount(metric.sample_size)}` : ""}
      </div>
      {metric.message ? (
        <p className="mt-1 text-xs leading-5 text-amber-800 dark:text-amber-200">{metric.message}</p>
      ) : null}
    </div>
  );
}

export function IntervalLine({ interval }: { interval: ConfidenceInterval | undefined }) {
  if (!interval) {
    return null;
  }
  if (interval.lower === null || interval.upper === null) {
    return (
      <p className="text-xs text-amber-800 dark:text-amber-200" data-testid="ci-withheld">
        {interval.message ?? "Interval withheld. A missing bound is not a zero."}
      </p>
    );
  }
  const width =
    interval.lower !== null && interval.upper !== null ? interval.upper - interval.lower : null;
  return (
    <div className="space-y-1 text-xs text-slate-500" data-testid="ci-line">
      <p>
        Percentile CI {formatInterval(interval.lower, interval.upper)}
        {width !== null ? (
          <>
            {" "}
            · width <span className="tabular">{formatRate(width)}</span> (upper − lower; wider =
            more resampling uncertainty under this procedure)
          </>
        ) : null}
      </p>
      <p>
        {interval.iterations} {interval.sampling_unit} resamples · seed {interval.seed} · method{" "}
        {interval.method}. Not proof of fairness.
      </p>
    </div>
  );
}

export function CannotConclude({ lines }: { lines: string[] }) {
  return (
    <Panel className="border-l-4 border-l-[#2563EB]">
      <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-[#2563EB]">
        What this cannot conclude
      </h2>
      <ul className="mt-3 space-y-3 text-sm leading-6 text-slate-700 dark:text-slate-200" data-testid="cannot-conclude">
        {lines.map((line) => (
          <li key={line}>{line}</li>
        ))}
      </ul>
    </Panel>
  );
}

export function ProvenanceCard({
  provenance,
}: {
  provenance: NonNullable<import("../types").AuditPayload["provenance"]>;
}) {
  const rows: Array<[string, string]> = [
    ["Dataset", provenance.dataset_name],
    ["Synthetic", provenance.is_synthetic ? "yes" : "no"],
    ["Rows", String(provenance.row_count)],
    ["SHA-256", provenance.content_sha256.slice(0, 16) + "…"],
    ["Code", provenance.code_version],
    ["Methodology", provenance.methodology_version ?? provenance.code_version],
    ["Fairlearn", provenance.fairlearn_version],
    ["scikit-learn", provenance.sklearn_version],
    ["Seed", String(provenance.seed)],
    ["Bootstrap", `${provenance.bootstrap_iterations} ${provenance.sampling_unit} resamples`],
    ["Minimum n", String(provenance.small_group_min_n)],
    ["Positive label", provenance.positive_label ?? "—"],
    ["Score", provenance.score_semantics ?? "not declared"],
  ];
  return (
    <Panel>
      <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">Provenance</h2>
      <dl className="mt-3 space-y-2 text-sm">
        {rows.map(([label, value]) => (
          <div key={label} className="flex justify-between gap-3">
            <dt className="text-slate-500">{label}</dt>
            <dd className="max-w-[180px] truncate text-right font-medium" title={value}>
              {value}
            </dd>
          </div>
        ))}
      </dl>
      {provenance.bootstrap_capped ? (
        <p className="mt-3 text-xs leading-5 text-amber-800 dark:text-amber-200">
          Requested {provenance.bootstrap_iterations_requested} resamples. The cap ran{" "}
          {provenance.bootstrap_iterations}.
        </p>
      ) : null}
    </Panel>
  );
}
