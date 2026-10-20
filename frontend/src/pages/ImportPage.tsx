import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Link, useNavigate } from "react-router";

import { ApiError, api } from "../api";
import { PageIntro } from "../components/Shell";
import { ErrorNote, Loading, Panel } from "../components/ui";
import type { DatasetSummary, Profile } from "../types";

export function ImportPage() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [error, setError] = useState<string | null>(null);
  const profiles = useQuery({
    queryKey: ["profiles"],
    queryFn: () => api<{ profiles: Profile[] }>("/api/synthetic-profiles"),
  });
  const datasets = useQuery({
    queryKey: ["datasets"],
    queryFn: () => api<{ datasets: DatasetSummary[] }>("/api/datasets"),
  });

  const generate = useMutation({
    mutationFn: (profile: string) =>
      api<DatasetSummary>("/api/datasets/synthetic", {
        method: "POST",
        body: JSON.stringify({ profile }),
      }),
    onSuccess: async (dataset) => {
      await queryClient.invalidateQueries({ queryKey: ["datasets"] });
      navigate(`/datasets/${dataset.id}/map`);
    },
    onError: (reason) => setError(reason instanceof ApiError ? reason.message : "The dataset was not created."),
  });

  const upload = useMutation({
    mutationFn: async (file: File) => {
      const body = new FormData();
      body.set("file", file);
      body.set("name", file.name);
      return api<DatasetSummary>("/api/datasets", { method: "POST", body });
    },
    onSuccess: async (dataset) => {
      await queryClient.invalidateQueries({ queryKey: ["datasets"] });
      navigate(`/datasets/${dataset.id}/map`);
    },
    onError: (reason) => setError(reason instanceof ApiError ? reason.message : "The file was rejected."),
  });

  return (
    <div>
      <PageIntro
        eyebrow="Import"
        title="Audit the model. Understand the trade-offs."
        lede="Upload an authorized evaluation file, or generate a deterministic synthetic table. No names and no personal data are included in the synthetic sets."
      />
      {error ? <div className="mb-4"><ErrorNote message={error} /></div> : null}
      {profiles.isLoading ? <Loading label="Loading synthetic profiles" /> : null}
      {profiles.isError ? <ErrorNote message="The profile list could not be loaded." /> : null}
      <div className="grid gap-4 lg:grid-cols-2">
        {(profiles.data?.profiles ?? []).map((profile) => (
          <Panel key={profile.id}>
            <p className="text-xs font-semibold uppercase tracking-[0.14em] text-[#2563EB]">Synthetic</p>
            <h2 className="mt-2 text-xl font-semibold">{profile.title}</h2>
            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">{profile.description}</p>
            <p className="mt-3 text-xs text-slate-500">{profile.row_count} constructed rows</p>
            <button
              type="button"
              className="mt-4 rounded-xl bg-[#2563EB] px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-60"
              data-testid={`generate-${profile.id}`}
              disabled={generate.isPending}
              onClick={() => {
                setError(null);
                generate.mutate(profile.id);
              }}
            >
              Generate this table
            </button>
          </Panel>
        ))}
      </div>
      <Panel className="mt-4">
        <h2 className="text-lg font-semibold">Upload CSV or Parquet</h2>
        <p className="mt-1 text-sm text-slate-600 dark:text-slate-300">
          CSV must be UTF-8. Parquet is read with pyarrow. Files stay on this machine.
        </p>
        <label className="mt-4 flex cursor-pointer flex-col items-start gap-2 rounded-xl border border-dashed border-slate-300 px-4 py-6 text-sm dark:border-white/15">
          <span className="font-medium">Choose a .csv or .parquet file</span>
          <input
            type="file"
            accept=".csv,.parquet,text/csv"
            className="text-sm"
            onChange={(event) => {
              const file = event.target.files?.[0];
              if (file) {
                setError(null);
                upload.mutate(file);
              }
            }}
          />
        </label>
      </Panel>
      <section className="mt-8">
        <h2 className="text-lg font-semibold">Datasets</h2>
        {datasets.isLoading ? <Loading label="Loading datasets" /> : null}
        {(datasets.data?.datasets.length ?? 0) === 0 && !datasets.isLoading ? (
          <p className="mt-2 text-sm text-slate-500">No datasets yet.</p>
        ) : null}
        <ul className="mt-3 divide-y divide-slate-200 overflow-hidden rounded-2xl border border-slate-200 bg-white dark:divide-white/10 dark:border-white/10 dark:bg-[#121826]">
          {(datasets.data?.datasets ?? []).map((dataset) => (
            <li key={dataset.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
              <div>
                <p className="font-medium">{dataset.name}</p>
                <p className="text-xs text-slate-500">
                  {dataset.row_count} rows · {dataset.is_synthetic ? "synthetic" : "upload"}
                  {dataset.latest_audit_status ? ` · audit ${dataset.latest_audit_status}` : ""}
                </p>
              </div>
              <div className="flex gap-3 text-sm">
                <Link className="text-[#2563EB]" to={`/datasets/${dataset.id}/map`}>
                  Mapping
                </Link>
                {dataset.latest_audit_id ? (
                  <Link className="text-[#2563EB]" to={`/audits/${dataset.latest_audit_id}/groups`}>
                    Open audit
                  </Link>
                ) : null}
              </div>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
