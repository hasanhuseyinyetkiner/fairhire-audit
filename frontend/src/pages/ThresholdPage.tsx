import { useMutation } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router";

import { ApiError, api, useAudit } from "../api";
import { PageIntro } from "../components/Shell";
import { CannotConclude, ErrorNote, Loading, Panel, RateReadout } from "../components/ui";
import { formatRate } from "../lib/format";
import type { ThresholdResult } from "../types";

export function ThresholdPage() {
  const { auditId = "" } = useParams();
  const audit = useAudit(auditId);
  const [threshold, setThreshold] = useState(0.5);
  const [error, setError] = useState<string | null>(null);
  const scenario = useMutation({
    mutationFn: (value: number) =>
      api<ThresholdResult>(`/api/audits/${auditId}/threshold-scenarios`, {
        method: "POST",
        body: JSON.stringify({ threshold: value }),
      }),
    onError: (reason) => setError(reason instanceof ApiError ? reason.message : "The scenario failed."),
  });

  if (audit.isLoading) return <Loading label="Loading the score gate" />;
  if (audit.isError || !audit.data?.score_gate) return <ErrorNote message="The audit could not be loaded." />;
  const gate = audit.data.score_gate;

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
      <div className="space-y-6">
        <PageIntro
          eyebrow="Threshold lab"
          title={gate.enabled ? "Simulate a cutoff" : "The lab is closed"}
          lede={gate.reason}
        />
        {error ? <ErrorNote message={error} /> : null}
        <Panel>
          <p className="text-sm">
            Calibrated claim: <strong>{gate.calibrated ? "yes" : "not made"}</strong>
          </p>
          {gate.brier_score !== null ? (
            <p className="mt-2 text-sm leading-6">
              Brier score <span className="tabular font-semibold">{gate.brier_score.toFixed(4)}</span>. {gate.brier_formula}
            </p>
          ) : null}
          {gate.reliability ? (
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
                {gate.reliability.map((bin) => (
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
        {gate.enabled ? (
          <Panel>
            <form
              className="flex flex-wrap items-end gap-4"
              onSubmit={(event) => {
                event.preventDefault();
                setError(null);
                scenario.mutate(threshold);
              }}
            >
              <label className="text-sm">
                <span className="font-medium">Threshold</span>
                <input
                  type="range"
                  min={gate.semantics === "probability" ? 0 : 0}
                  max={gate.semantics === "probability" ? 1 : 1}
                  step={0.01}
                  value={Math.min(1, Math.max(0, threshold))}
                  onChange={(event) => setThreshold(Number(event.target.value))}
                  className="mt-2 block w-64"
                  aria-valuetext={String(threshold)}
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
                />
              </label>
              <button
                type="submit"
                className="rounded-xl bg-[#2563EB] px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
                disabled={scenario.isPending}
              >
                {scenario.isPending ? "Computing…" : "Apply threshold"}
              </button>
            </form>
            <p className="mt-3 text-xs text-slate-500">
              The slider covers 0 to 1. The number field accepts other finite cutoffs for ranking scores.
            </p>
          </Panel>
        ) : (
          <Panel>
            <p className="text-sm leading-6">No cutoff is simulated while the gate is closed. There is no placeholder chart.</p>
          </Panel>
        )}
        {scenario.data ? (
          <div className="space-y-4">
            <Panel>
              <p className="text-sm leading-6">{scenario.data.note}</p>
              <p className="mt-2 text-xs text-slate-500">
                Point estimates only: {scenario.data.point_estimates_only ? "yes" : "no"}. Threshold{" "}
                {scenario.data.threshold}.
              </p>
            </Panel>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {scenario.data.metrics
                .filter((metric) => ["accuracy", "precision", "recall", "fpr", "fnr", "selection_rate"].includes(metric.name))
                .map((metric) => (
                  <Panel key={metric.name}>
                    <RateReadout metric={metric} />
                  </Panel>
                ))}
            </div>
          </div>
        ) : null}
      </div>
      <aside>
        <CannotConclude lines={audit.data.cannot_conclude} />
      </aside>
    </div>
  );
}
