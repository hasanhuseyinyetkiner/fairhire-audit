import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useNavigate, useParams } from "react-router";

import { ApiError, api } from "../api";
import { PageIntro } from "../components/Shell";
import { ErrorNote, Loading, Panel } from "../components/ui";
import type { AuditPayload, DatasetSummary } from "../types";

export function MapPage() {
  const { datasetId = "" } = useParams();
  const dataset = useQuery({
    queryKey: ["dataset", datasetId],
    queryFn: () => api<DatasetSummary>(`/api/datasets/${datasetId}`),
  });
  const preview = useQuery({
    queryKey: ["preview", datasetId],
    queryFn: () =>
      api<{ columns: string[]; rows: Record<string, unknown>[]; row_count: number }>(
        `/api/datasets/${datasetId}/preview`,
      ),
  });
  if (dataset.isLoading || preview.isLoading) return <Loading label="Loading the file" />;
  if (dataset.isError || preview.isError || !dataset.data || !preview.data) {
    return <ErrorNote message="The dataset could not be loaded." />;
  }

  return (
    <MapForm
      datasetId={datasetId}
      name={dataset.data.name}
      columns={preview.data.columns}
      rows={preview.data.rows}
      rowCount={preview.data.row_count}
      mapping={dataset.data.mapping}
    />
  );
}

function MapForm({
  datasetId,
  name,
  columns,
  rows,
  rowCount,
  mapping,
}: {
  datasetId: string;
  name: string;
  columns: string[];
  rows: Record<string, unknown>[];
  rowCount: number;
  mapping: DatasetSummary["mapping"];
}) {
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const [yTrue, setYTrue] = useState(mapping?.y_true ?? (columns.includes("y_true") ? "y_true" : ""));
  const [yPred, setYPred] = useState(mapping?.y_pred ?? (columns.includes("y_pred") ? "y_pred" : ""));
  const [yAlt, setYAlt] = useState(mapping?.y_pred_alt ?? "");
  const [score, setScore] = useState(mapping?.score ?? (columns.includes("score") ? "score" : ""));
  const [semantics, setSemantics] = useState<"" | "probability" | "ranking_score">(
    mapping?.score_semantics ?? "",
  );
  const [weight, setWeight] = useState(
    mapping?.sample_weight ?? (columns.includes("sample_weight") ? "sample_weight" : ""),
  );
  const [timestamp, setTimestamp] = useState(mapping?.timestamp_column ?? "");
  const [positive, setPositive] = useState(mapping?.positive_label ?? "1");
  const [sensitive, setSensitive] = useState<string[]>(
    mapping?.sensitive_columns ?? (columns.includes("group") ? ["group"] : []),
  );

  const run = useMutation({
    mutationFn: async () => {
      await api(`/api/datasets/${datasetId}/mapping`, {
        method: "POST",
        body: JSON.stringify({
          y_true: yTrue,
          y_pred: yPred || null,
          y_pred_alt: yAlt || null,
          score: score || null,
          score_semantics: score ? semantics || null : null,
          sensitive_columns: sensitive,
          sample_weight: weight || null,
          timestamp_column: timestamp || null,
          positive_label: positive,
        }),
      });
      return api<AuditPayload>("/api/audits", {
        method: "POST",
        body: JSON.stringify({ dataset_id: datasetId }),
      });
    },
    onSuccess: (audit) => navigate(`/audits/${audit.id}/quality`),
    onError: (reason) => setError(reason instanceof ApiError ? reason.message : "The audit did not run."),
  });

  function toggleSensitive(column: string) {
    setSensitive((current) =>
      current.includes(column) ? current.filter((item) => item !== column) : [...current, column],
    );
  }

  return (
    <div>
      <PageIntro
        eyebrow="Column mapping"
        title={name}
        lede="Choose the outcome, the prediction, and the group columns you are permitted to audit. The tool does not infer a protected attribute."
      />
      {error ? <div className="mb-4"><ErrorNote message={error} /></div> : null}
      <Panel className="overflow-x-auto">
        <h2 className="text-sm font-semibold uppercase tracking-[0.14em] text-slate-500">Preview</h2>
        <table className="mt-3 w-full text-left text-sm">
          <thead>
            <tr>
              {columns.map((column) => (
                <th key={column} className="border-b border-slate-200 px-2 py-2 font-medium dark:border-white/10">
                  {column}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, index) => (
              <tr key={index}>
                {columns.map((column) => (
                  <td key={column} className="border-b border-slate-100 px-2 py-2 tabular dark:border-white/5">
                    {String(row[column] ?? "")}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-2 text-xs text-slate-500">{rowCount} rows in the file. Eight are shown.</p>
      </Panel>
      <form
        className="mt-4 grid gap-4 lg:grid-cols-2"
        onSubmit={(event) => {
          event.preventDefault();
          setError(null);
          run.mutate();
        }}
      >
        <Field label="Actual outcome" value={yTrue} columns={columns} onChange={setYTrue} required />
        <Field label="Prediction" value={yPred} columns={columns} onChange={setYPred} optional />
        <Field label="Second prediction" value={yAlt} columns={columns} onChange={setYAlt} optional />
        <Field label="Score" value={score} columns={columns} onChange={setScore} optional />
        <label className="text-sm">
          <span className="font-medium">Score semantics</span>
          <select
            className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 dark:border-white/10 dark:bg-[#0f172a]"
            value={semantics}
            onChange={(event) => setSemantics(event.target.value as "" | "probability" | "ranking_score")}
          >
            <option value="">Not declared</option>
            <option value="probability">Probability in [0, 1]</option>
            <option value="ranking_score">Ranking score</option>
          </select>
        </label>
        <Field label="Sample weight" value={weight} columns={columns} onChange={setWeight} optional />
        <Field label="Timestamp (recorded, unused)" value={timestamp} columns={columns} onChange={setTimestamp} optional />
        <label className="text-sm">
          <span className="font-medium">Positive label</span>
          <input
            className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 dark:border-white/10 dark:bg-[#0f172a]"
            value={positive}
            onChange={(event) => setPositive(event.target.value)}
          />
        </label>
        <fieldset className="lg:col-span-2">
          <legend className="text-sm font-medium">Group columns for this audit</legend>
          <div className="mt-2 flex flex-wrap gap-3">
            {columns.map((column) => (
              <label key={column} className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={sensitive.includes(column)}
                  onChange={() => toggleSensitive(column)}
                />
                {column}
              </label>
            ))}
          </div>
        </fieldset>
        <div className="lg:col-span-2">
          <button
            type="submit"
            className="rounded-xl bg-[#2563EB] px-4 py-2 text-sm font-medium text-white disabled:opacity-60"
            disabled={run.isPending || !yTrue || sensitive.length === 0}
          >
            {run.isPending ? "Computing metrics…" : "Run audit"}
          </button>
          {mapping ? <p className="mt-2 text-xs text-slate-500">A mapping is already saved. Running replaces it for the next audit.</p> : null}
        </div>
      </form>
    </div>
  );
}

function Field({
  label,
  value,
  columns,
  onChange,
  required = false,
  optional = false,
}: {
  label: string;
  value: string;
  columns: string[];
  onChange: (value: string) => void;
  required?: boolean;
  optional?: boolean;
}) {
  return (
    <label className="text-sm">
      <span className="font-medium">
        {label}
        {optional ? <span className="text-slate-400"> · optional</span> : null}
      </span>
      <select
        required={required}
        className="mt-1 w-full rounded-xl border border-slate-200 bg-white px-3 py-2 dark:border-white/10 dark:bg-[#0f172a]"
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">{optional ? "Not mapped" : "Select a column"}</option>
        {columns.map((column) => (
          <option key={column} value={column}>
            {column}
          </option>
        ))}
      </select>
    </label>
  );
}
