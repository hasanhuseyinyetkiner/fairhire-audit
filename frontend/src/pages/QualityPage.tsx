import { useParams } from "react-router";

import { useAudit } from "../api";
import { PageIntro } from "../components/Shell";
import { CannotConclude, ErrorNote, FormulaTip, Loading, Panel, ProvenanceCard, RateReadout } from "../components/ui";
import { formatCount } from "../lib/format";
import type { Metric } from "../types";

const HEADLINE = ["accuracy", "balanced_accuracy", "precision", "recall", "fpr", "fnr"];

export function QualityPage() {
  const { auditId = "" } = useParams();
  const audit = useAudit(auditId);
  if (audit.isLoading) return <Loading label="Loading model quality" />;
  if (audit.isError || !audit.data) return <ErrorNote message="The audit could not be loaded." />;
  const data = audit.data;
  if (data.status !== "succeeded" || !data.confusion_matrix || !data.provenance) {
    return <ErrorNote message={data.failure_reason ?? "This audit has no metrics."} />;
  }
  const byName = Object.fromEntries(data.metrics.map((metric) => [metric.name, metric]));
  const matrix = data.confusion_matrix;

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
      <div className="space-y-6">
        <PageIntro
          eyebrow="Model quality"
          title="Overall counts, then the rates"
          lede="Every figure on this page is from the audit response. A missing rate is undefined, not zero."
        />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {HEADLINE.map((name) => (
            <Panel key={name}>
              <RateReadout metric={byName[name]} />
            </Panel>
          ))}
        </div>
        <Panel>
          <h2 className="text-lg font-semibold">Confusion matrix</h2>
          <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">{matrix.convention}</p>
          <div className="mt-4 grid grid-cols-[120px_1fr_1fr] gap-2" data-testid="confusion-matrix">
            <div />
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Predicted 0</div>
            <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">Predicted 1</div>
            <div className="self-center text-xs font-semibold uppercase tracking-wide text-slate-500">Actual 0</div>
            <Cell name="TN" value={matrix.tn} />
            <Cell name="FP" value={matrix.fp} />
            <div className="self-center text-xs font-semibold uppercase tracking-wide text-slate-500">Actual 1</div>
            <Cell name="FN" value={matrix.fn} />
            <Cell name="TP" value={matrix.tp} accent />
          </div>
          <p className="mt-3 text-xs text-slate-500">Sample size {data.sample_size}. Counts include every row.</p>
        </Panel>
        <Panel>
          <h2 className="text-lg font-semibold">All overall rates</h2>
          <MetricTable metrics={data.metrics} />
        </Panel>
        <Panel>
          <h2 className="text-lg font-semibold">Second prediction</h2>
          <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{data.comparison?.reason}</p>
          {data.comparison?.available ? (
            <table className="mt-3 w-full text-left text-sm">
              <thead>
                <tr className="text-xs uppercase tracking-wide text-slate-500">
                  <th className="py-2">Metric</th>
                  <th>Primary</th>
                  <th>Alternate</th>
                  <th>Primary − alternate</th>
                </tr>
              </thead>
              <tbody>
                {data.comparison.deltas.map((delta) => (
                  <tr key={delta.name} className="border-t border-slate-100 dark:border-white/10">
                    <td className="py-2">{delta.label}</td>
                    <td className="tabular">{delta.primary ?? "—"}</td>
                    <td className="tabular">{delta.alternate ?? "—"}</td>
                    <td className="tabular">{delta.delta ?? delta.message ?? "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : null}
        </Panel>
        {data.warnings.length > 0 ? (
          <Panel>
            <h2 className="text-lg font-semibold">Warnings</h2>
            <ul className="mt-2 list-disc space-y-2 pl-5 text-sm leading-6">
              {data.warnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </Panel>
        ) : null}
      </div>
      <aside className="space-y-4">
        <ProvenanceCard provenance={data.provenance} />
        <CannotConclude lines={data.cannot_conclude} />
      </aside>
    </div>
  );
}

function Cell({ name, value, accent = false }: { name: string; value: number; accent?: boolean }) {
  return (
    <div
      className={`rounded-2xl border px-4 py-5 ${
        accent ? "border-[#2563EB] bg-blue-50 dark:bg-blue-950/30" : "border-slate-200 dark:border-white/10"
      }`}
    >
      <div className="text-xs font-semibold uppercase tracking-wide text-slate-500">{name}</div>
      <div className="tabular mt-1 text-3xl font-semibold">{formatCount(value)}</div>
    </div>
  );
}

function MetricTable({ metrics }: { metrics: Metric[] }) {
  return (
    <table className="mt-3 w-full text-left text-sm">
      <thead>
        <tr className="text-xs uppercase tracking-wide text-slate-500">
          <th className="py-2">Metric</th>
          <th>Value</th>
          <th>Count</th>
        </tr>
      </thead>
      <tbody>
        {metrics.map((metric) => (
          <tr key={metric.name} className="border-t border-slate-100 dark:border-white/10">
            <td className="py-2">
              <span className="inline-flex items-center gap-1">
                {metric.label}
                <FormulaTip formula={metric.formula} />
              </span>
            </td>
            <td className="tabular">{metric.value === null ? "—" : metric.value.toFixed(4)}</td>
            <td className="tabular text-slate-500">
              {metric.numerator === null ? "withheld" : `${formatCount(metric.numerator)} / ${formatCount(metric.denominator)}`}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
