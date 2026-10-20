import { useParams } from "react-router";

import { useAudit } from "../api";
import { PageIntro } from "../components/Shell";
import { CannotConclude, ErrorNote, Loading, Panel, ProvenanceCard } from "../components/ui";
import { formatRate } from "../lib/format";

export function ReportPage() {
  const { auditId = "" } = useParams();
  const audit = useAudit(auditId);
  if (audit.isLoading) return <Loading label="Loading the report" />;
  if (audit.isError || !audit.data) return <ErrorNote message="The report could not be loaded." />;
  const data = audit.data;
  if (!data.provenance || !data.confusion_matrix) {
    return <ErrorNote message={data.failure_reason ?? "This audit has no report."} />;
  }
  const measured = data.metrics.filter((metric) =>
    ["accuracy", "balanced_accuracy", "precision", "recall", "fpr", "fnr"].includes(metric.name),
  );

  return (
    <div className="space-y-6">
      <PageIntro
        eyebrow="Audit report"
        title="A record of the evidence"
        lede="This page repeats the API payload. Downloaded HTML and JSON are the same record. Neither is a certificate."
      />
      <div className="flex flex-wrap gap-3">
        <a className="rounded-xl bg-[#2563EB] px-4 py-2 text-sm font-medium text-white" href={`/api/audits/${auditId}/report.html`}>
          Download HTML
        </a>
        <a
          className="rounded-xl border border-slate-300 px-4 py-2 text-sm font-medium dark:border-white/15"
          href={`/api/audits/${auditId}/report.json`}
        >
          Download JSON
        </a>
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <Panel>
          <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">What was measured</h2>
          <ul className="mt-4 space-y-3">
            {measured.map((metric) => (
              <li key={metric.name} className="flex items-baseline justify-between gap-3 border-b border-slate-100 pb-2 dark:border-white/10">
                <span>{metric.label}</span>
                <span className="tabular text-lg font-semibold">{formatRate(metric.value)}</span>
              </li>
            ))}
          </ul>
          <p className="mt-4 text-sm leading-6 text-slate-600 dark:text-slate-300">
            Confusion matrix TN {data.confusion_matrix.tn}, FP {data.confusion_matrix.fp}, FN{" "}
            {data.confusion_matrix.fn}, TP {data.confusion_matrix.tp}. Sample size {data.sample_size}.
          </p>
        </Panel>
        <CannotConclude lines={data.cannot_conclude} />
      </div>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_300px]">
        <Panel>
          <h2 className="text-lg font-semibold">Assumptions</h2>
          <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6">
            {data.assumptions.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
          {data.warnings.length > 0 ? (
            <>
              <h2 className="mt-6 text-lg font-semibold">Unresolved on this run</h2>
              <ul className="mt-3 list-disc space-y-2 pl-5 text-sm leading-6">
                {data.warnings.map((line) => (
                  <li key={line}>{line}</li>
                ))}
              </ul>
            </>
          ) : null}
        </Panel>
        <ProvenanceCard provenance={data.provenance} />
      </div>
    </div>
  );
}
