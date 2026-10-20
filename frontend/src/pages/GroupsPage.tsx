import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useParams } from "react-router";
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

import { api, useAudit } from "../api";
import { PageIntro } from "../components/Shell";
import { CannotConclude, ErrorNote, IntervalLine, Loading, Panel, ProvenanceCard, RateReadout } from "../components/ui";
import { formatRate } from "../lib/format";
import type { ConfidenceInterval, GroupColumn, GroupView, Metric } from "../types";

const COLORS = ["#2563EB", "#0F766E", "#B45309", "#7C3AED"];
const CHART_METRICS = ["recall", "fpr", "fnr", "selection_rate"];

export function GroupsPage() {
  const { auditId = "" } = useParams();
  const [intersection, setIntersection] = useState(false);
  const audit = useAudit(auditId);
  const view = useQuery({
    queryKey: ["groups", auditId, intersection],
    queryFn: () => api<GroupView>(`/api/audits/${auditId}/groups?intersection=${intersection}`),
    enabled: Boolean(auditId),
  });

  if (audit.isLoading || view.isLoading) return <Loading label="Loading group disparities" />;
  if (audit.isError || view.isError || !audit.data || !view.data) {
    return <ErrorNote message="Group results could not be loaded." />;
  }
  const column = view.data.groups[0];
  const intervals = audit.data.confidence_intervals;

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_300px]">
      <div className="space-y-6">
        <PageIntro
          eyebrow="Group disparities"
          title="Same rows. Different error rates."
          lede="Fairlearn MetricFrame supplies the group rates that have a denominator. Differences use Fairlearn on groups that clear the sample-size minimum. Suppressed groups are not drawn as zero."
        />
        <div className="flex flex-wrap items-center gap-3">
          <button
            type="button"
            className="rounded-xl border border-slate-200 px-3 py-2 text-sm dark:border-white/10"
            aria-pressed={intersection}
            onClick={() => setIntersection((value) => !value)}
          >
            {intersection ? "Showing intersection" : "Show intersection"}
          </button>
          <p className="text-sm text-slate-600 dark:text-slate-300">{view.data.note}</p>
        </div>
        {!view.data.available || !column ? (
          <Panel>
            <p className="text-sm leading-6">{view.data.note}</p>
          </Panel>
        ) : (
          <>
            <div className="grid gap-4 lg:grid-cols-3">
              {column.groups.map((group) => (
                <article
                  key={group.group_value}
                  data-testid={`group-card-${group.group_value}`}
                  className={`rounded-2xl border p-4 ${
                    group.suppressed
                      ? "border-dashed border-amber-400 bg-amber-50/60 dark:border-amber-700 dark:bg-amber-950/20"
                      : "border-slate-200 bg-white dark:border-white/10 dark:bg-[#121826]"
                  }`}
                >
                  <div className="flex items-baseline justify-between gap-2">
                    <h2 className="text-lg font-semibold">{group.group_value}</h2>
                    <span className="rounded-full bg-slate-100 px-2 py-1 text-xs font-medium tabular dark:bg-white/10">
                      n = {group.sample_size}
                    </span>
                  </div>
                  {group.suppressed ? (
                    <p className="mt-3 text-sm leading-6">{group.message}</p>
                  ) : (
                    <ul className="mt-3 space-y-3">
                      {["accuracy", "fpr", "fnr", "recall", "selection_rate"].map((name) => {
                        const metric = metricByName(group.metrics, name);
                        return (
                          <li key={name}>
                            <RateReadout metric={metric} />
                            <Meter value={metric.value} />
                            <IntervalLine
                              interval={findInterval(intervals, name, column.column, group.group_value)}
                            />
                          </li>
                        );
                      })}
                    </ul>
                  )}
                </article>
              ))}
            </div>
            <Panel>
              <h2 className="text-lg font-semibold">Side-by-side rates</h2>
              <p className="mt-1 text-sm text-slate-500">
                Undefined rates are omitted from the chart. Sample sizes are in the legend.
              </p>
              <div className="mt-4 h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartRows(column)}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="label" />
                    <YAxis domain={[0, 1]} tickFormatter={(value) => formatRate(Number(value))} />
                    <Tooltip formatter={(value) => formatRate(Number(value))} />
                    <Legend />
                    {column.groups
                      .filter((group) => !group.suppressed)
                      .map((group, index) => (
                        <Bar
                          key={group.group_value}
                          dataKey={group.group_value}
                          name={`${group.group_value} (n=${group.sample_size})`}
                          fill={COLORS[index % COLORS.length]}
                          radius={4}
                        />
                      ))}
                  </BarChart>
                </ResponsiveContainer>
              </div>
              <table className="mt-4 w-full text-left text-sm">
                <caption className="sr-only">Group rates and sample sizes</caption>
                <thead>
                  <tr className="text-xs uppercase tracking-wide text-slate-500">
                    <th className="py-2">Group</th>
                    <th>n</th>
                    {CHART_METRICS.map((name) => (
                      <th key={name}>{name}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {column.groups.map((group) => (
                    <tr key={group.group_value} className="border-t border-slate-100 dark:border-white/10">
                      <td className="py-2">{group.group_value}</td>
                      <td className="tabular">{group.sample_size}</td>
                      {CHART_METRICS.map((name) => (
                        <td key={name} className="tabular">
                          {group.suppressed ? "withheld" : formatRate(metricByName(group.metrics, name).value)}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </Panel>
            <Panel>
              <h2 className="text-lg font-semibold">Fairlearn differences</h2>
              <ul className="mt-3 space-y-4">
                {column.disparities.map((item) => (
                  <li key={item.name} className="border-t border-slate-100 pt-3 first:border-0 first:pt-0 dark:border-white/10">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <h3 className="font-medium">{item.label}</h3>
                      <span className="tabular text-2xl font-semibold">{formatRate(item.value)}</span>
                    </div>
                    <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.formula}</p>
                    <p className="mt-1 text-xs text-slate-500">
                      Included: {item.groups_included.join(", ") || "none"}. Excluded:{" "}
                      {item.groups_excluded.join(", ") || "none"}. Method: {item.method}.
                    </p>
                    {item.message ? <p className="mt-1 text-sm text-amber-800 dark:text-amber-200">{item.message}</p> : null}
                    <IntervalLine interval={findInterval(intervals, item.name, column.column, null)} />
                  </li>
                ))}
              </ul>
            </Panel>
          </>
        )}
      </div>
      <aside className="space-y-4">
        {audit.data.provenance ? <ProvenanceCard provenance={audit.data.provenance} /> : null}
        <CannotConclude lines={view.data.cannot_conclude} />
      </aside>
    </div>
  );
}

function metricByName(metrics: Metric[], name: string) {
  const found = metrics.find((metric) => metric.name === name);
  if (!found) {
    throw new Error(`Missing metric ${name}`);
  }
  return found;
}

function findInterval(
  intervals: ConfidenceInterval[],
  name: string,
  column: string,
  group: string | null,
): ConfidenceInterval | undefined {
  return intervals.find(
    (interval) =>
      interval.metric_name === name &&
      interval.group_column === column &&
      interval.group_value === group,
  );
}

function chartRows(column: GroupColumn) {
  return CHART_METRICS.map((name) => {
    const row: Record<string, string | number> = {
      label: name === "recall" ? "Recall" : name === "selection_rate" ? "Selection" : name.toUpperCase(),
    };
    for (const group of column.groups) {
      if (group.suppressed) continue;
      const value = metricByName(group.metrics, name).value;
      if (value !== null) row[group.group_value] = value;
    }
    return row;
  });
}

function Meter({ value }: { value: number | null }) {
  if (value === null) return null;
  return (
    <div className="mt-1 h-1.5 rounded-full bg-slate-100 dark:bg-white/10" aria-hidden="true">
      <div className="h-1.5 rounded-full bg-[#2563EB]" style={{ width: `${Math.min(100, Math.max(0, value * 100))}%` }} />
    </div>
  );
}
