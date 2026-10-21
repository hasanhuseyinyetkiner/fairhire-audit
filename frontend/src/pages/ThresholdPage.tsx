import { useMutation, useQuery } from "@tanstack/react-query";
import { useEffect, useRef, useState } from "react";
import { useParams } from "react-router";

import { ApiError, api, useAudit } from "../api";
import { PageIntro } from "../components/Shell";
import { CannotConclude, ErrorNote, Loading, Panel, RateReadout } from "../components/ui";
import { formatRate } from "../lib/format";
import type { Meta, ThresholdResult } from "../types";

const DEBOUNCE_MS = 200;

export function ThresholdPage() {
  const { auditId = "" } = useParams();
  const audit = useAudit(auditId);
  const meta = useQuery({
    queryKey: ["meta"],
    queryFn: () => api<Meta>("/api/meta"),
  });
  const [threshold, setThreshold] = useState(0.5);
  const [error, setError] = useState<string | null>(null);
  const [liveResult, setLiveResult] = useState<ThresholdResult | null>(null);
  const requestId = useRef(0);
  const scenario = useMutation({
    mutationFn: (value: number) =>
      api<ThresholdResult>(`/api/audits/${auditId}/threshold-scenarios`, {
        method: "POST",
        body: JSON.stringify({ threshold: value }),
      }),
    // Lifecycle callbacks belong on useMutation options, not MutateOptions.
    // Clear prior error when a new attempt starts; set/clear error only for the latest request id.
    onMutate: () => {
      setError(null);
    },
  });

  const gate = audit.data?.score_gate;
  const enabled = Boolean(gate?.enabled);

  useEffect(() => {
    if (!enabled || !auditId) return;
    const id = ++requestId.current;
    const timer = window.setTimeout(() => {
      void scenario.mutateAsync(threshold).then(
        (data) => {
          // Ignore out-of-order responses from rapid slider changes.
          if (id !== requestId.current) return;
          setLiveResult(data);
          setError(null);
        },
        (reason) => {
          // Stale network failures must not overwrite a newer success or clear.
          if (id !== requestId.current) return;
          setError(reason instanceof ApiError ? reason.message : "The scenario failed.");
        },
      );
    }, DEBOUNCE_MS);
    return () => window.clearTimeout(timer);
    // scenario.mutateAsync is stable enough for debounce; avoid re-firing on mutation identity.
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentional: live slider updates
  }, [threshold, enabled, auditId]);

  if (audit.isLoading) return <Loading label="Loading the score gate" />;
  if (audit.isError || !audit.data?.score_gate) return <ErrorNote message="The audit could not be loaded." />;

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
      <div className="space-y-6">
        <PageIntro
          eyebrow="Threshold lab"
          title={gate!.enabled ? "Simulate a cutoff" : "The lab is closed"}
          lede={gate!.reason}
        />
        {error ? <ErrorNote message={error} /> : null}
        <Panel data-testid="threshold-methodology">
          <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">
            Methodology
          </h2>
          <dl className="mt-3 space-y-2 text-sm">
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">Version</dt>
              <dd className="font-medium" data-testid="methodology-version">
                {meta.data?.methodology_version ?? audit.data.provenance?.methodology_version ?? "—"}
              </dd>
            </div>
            <div className="flex justify-between gap-3">
              <dt className="text-slate-500">CMH</dt>
              <dd className="max-w-[220px] text-right text-xs leading-5">
                {meta.data?.cmh_note ?? "Not implemented — no multi-stratum design input."}
              </dd>
            </div>
          </dl>
          <p className="mt-3 text-xs leading-5 text-slate-500" data-testid="null-not-zero">
            {meta.data?.null_not_zero ??
              "JSON null rates mean undefined or withheld. They are not zeros."}
          </p>
          <p className="mt-2 text-xs leading-5 text-slate-500">
            Threshold Lab returns point estimates only (no live bootstrap CI). Audit-page percentile
            CI width is upper − lower under row resampling — uncertainty under that procedure, not
            proof of fairness.
          </p>
        </Panel>
        <Panel>
          <p className="text-sm">
            Calibrated claim: <strong>{gate!.calibrated ? "yes" : "not made"}</strong>
          </p>
          {gate!.brier_score !== null ? (
            <p className="mt-2 text-sm leading-6">
              Brier score <span className="tabular font-semibold">{gate!.brier_score.toFixed(4)}</span>. {gate!.brier_formula}
            </p>
          ) : null}
          {gate!.reliability ? (
            <table className="mt-4 w-full text-left text-sm">
              <caption className="mb-2 text-left text-sm font-medium">Reliability table</caption>
              <thead>
                <tr className="text-xs uppercase tracking-wide text-slate-500">
                  <th className="py-2">Bin</th>
                  <th>n</th>
                  <th>Mean score</th>
                  <th>Observed rate</th>
                </tr>
              </thead>
              <tbody>
                {gate!.reliability.map((bin) => (
                  <tr key={bin.bin_start} className="border-t border-slate-100 dark:border-white/10">
                    <td className="py-2 tabular">
                      {bin.bin_start.toFixed(1)}–{bin.bin_end.toFixed(1)}
                    </td>
                    <td className="tabular">{bin.count}</td>
                    <td className="tabular">{bin.mean_predicted === null ? "—" : bin.mean_predicted.toFixed(2)}</td>
                    <td className="tabular">
                      {formatRate(bin.observed_rate)}
                      {bin.message ? <span className="mt-1 block text-xs text-amber-800 dark:text-amber-200">{bin.message}</span> : null}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </Panel>
        {gate!.enabled ? (
          <Panel>
            <div className="flex flex-wrap items-end gap-4">
              <label className="text-sm">
                <span className="font-medium">Threshold</span>
                <input
                  type="range"
                  min={0}
                  max={1}
                  step={0.01}
                  value={Math.min(1, Math.max(0, threshold))}
                  onChange={(event) => setThreshold(Number(event.target.value))}
                  className="mt-2 block w-64 accent-[#2563EB]"
                  aria-label="Decision threshold"
                  aria-valuetext={String(threshold)}
                  data-testid="threshold-slider"
                />
              </label>
              <label className="text-sm">
                <span className="font-medium">Value</span>
                <input
                  type="number"
                  step="0.01"
                  value={threshold}
                  onChange={(event) => setThreshold(Number(event.target.value))}
                  className="mt-1 block w-28 rounded-xl border border-slate-200 px-3 py-2 dark:border-white/10 dark:bg-[#0f172a]"
                  aria-label="Threshold value"
                  data-testid="threshold-value"
                />
              </label>
              <p className="text-xs text-slate-500" aria-live="polite">
                {scenario.isPending ? "Updating metrics…" : "Metrics update as you move the slider."}
              </p>
            </div>
            <p className="mt-3 text-xs text-slate-500">
              The slider covers 0 to 1. The number field accepts other finite cutoffs for ranking scores.
            </p>
          </Panel>
        ) : (
          <Panel>
            <p className="text-sm leading-6">No cutoff is simulated while the gate is closed. There is no placeholder chart.</p>
          </Panel>
        )}
        {liveResult ? (
          <div className="space-y-4" data-testid="threshold-results">
            <Panel>
              <p className="text-sm leading-6">{liveResult.note}</p>
              <p className="mt-2 text-xs text-slate-500">
                Point estimates only: {liveResult.point_estimates_only ? "yes" : "no"}. Threshold{" "}
                <span className="tabular font-medium">{liveResult.threshold}</span>.
              </p>
            </Panel>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {liveResult.metrics
                .filter((metric) => ["accuracy", "precision", "recall", "fpr", "fnr", "selection_rate"].includes(metric.name))
                .map((metric) => (
                  <Panel key={metric.name}>
                    <RateReadout metric={metric} />
                  </Panel>
                ))}
            </div>
            {liveResult.groups[0]?.selection_audit?.pairs.length ? (
              <Panel>
                <h2 className="text-lg font-semibold">AIR at this cutoff</h2>
                <p className="mt-1 text-sm text-slate-500">
                  Live selection-rate ratios from the thresholded predictions. Descriptive only.
                </p>
                <ul className="mt-3 space-y-2 text-sm">
                  {liveResult.groups[0].selection_audit!.pairs.map((pair) => (
                    <li key={`${pair.focal_group}:${pair.reference_group}`} className="flex flex-wrap justify-between gap-2">
                      <span>
                        {pair.focal_group} / {pair.reference_group}
                      </span>
                      <span className={`tabular font-semibold ${pair.below_four_fifths ? "text-amber-700 dark:text-amber-300" : ""}`}>
                        {pair.value === null ? "—" : pair.value.toFixed(3)}
                      </span>
                    </li>
                  ))}
                </ul>
              </Panel>
            ) : null}
          </div>
        ) : null}
      </div>
      <aside>
        <CannotConclude lines={audit.data.cannot_conclude} />
      </aside>
    </div>
  );
}
