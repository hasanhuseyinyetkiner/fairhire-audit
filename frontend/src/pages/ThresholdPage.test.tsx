import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router";

import { ApiError } from "../api";
import { ThresholdPage } from "./ThresholdPage";

const mutateAsync = vi.fn();
const useAuditMock = vi.fn();

vi.mock("../api", async () => {
  const actual = await vi.importActual<typeof import("../api")>("../api");
  return {
    ...actual,
    useAudit: (...args: unknown[]) => useAuditMock(...args),
    api: vi.fn(async (path: string) => {
      if (path === "/api/meta") {
        return {
          name: "FairHire Audit",
          version: "0.1.0",
          methodology_version: "0.1.0",
          app_env: "test",
          demo: false,
          banner: null,
          fairlearn_version: "0.15.0",
          decision_engine: false,
          bootstrap_cap: 1000,
          small_group_min_n: 30,
          retention_days: 30,
          null_not_zero: "JSON null rates mean undefined or withheld. They are not zeros.",
          cmh_available: false,
          cmh_note: "Cochran–Mantel–Haenszel is not implemented.",
        };
      }
      throw new Error(`Unexpected api path ${path}`);
    }),
  };
});

vi.mock("@tanstack/react-query", async () => {
  const actual = await vi.importActual<typeof import("@tanstack/react-query")>("@tanstack/react-query");
  return {
    ...actual,
    useMutation: () => ({
      mutateAsync,
      isPending: false,
    }),
  };
});

const gateEnabledAudit = {
  isLoading: false,
  isError: false,
  data: {
    id: "audit-1",
    dataset_id: "ds-1",
    status: "succeeded",
    failure_reason: null,
    failure_code: null,
    decision_engine: false,
    sample_size: 204,
    confusion_matrix: null,
    metrics: [],
    comparison: null,
    groups: [],
    confidence_intervals: [],
    score_gate: {
      enabled: true,
      semantics: "probability",
      reason: "Score declared as probability.",
      brier_score: 0.1,
      brier_formula: "brier",
      reliability: null,
      calibrated: false,
    },
    warnings: [],
    assumptions: [],
    cannot_conclude: ["These figures do not certify legal compliance."],
    provenance: {
      dataset_id: "ds-1",
      dataset_name: "fixture",
      is_synthetic: true,
      synthetic_profile: "similar_accuracy_different_errors",
      content_sha256: "abc",
      row_count: 204,
      code_version: "0.1.0",
      methodology_version: "0.1.0",
      git_sha: null,
      fairlearn_version: "0.15.0",
      sklearn_version: "1.0",
      numpy_version: "2.0",
      scipy_version: "1.0",
      pandas_version: "2.0",
      seed: 1,
      bootstrap_iterations: 40,
      bootstrap_iterations_requested: 40,
      bootstrap_capped: false,
      bootstrap_method: "percentile",
      sampling_unit: "row",
      small_group_min_n: 30,
      positive_label: "1",
      score_semantics: "probability",
      mapping: {},
      started_at: null,
      finished_at: null,
    },
  },
};

const successPayload = {
  id: "s1",
  audit_id: "audit-1",
  threshold: 0.6,
  score_semantics: "probability",
  note: "Simulation only.",
  point_estimates_only: true,
  sample_size: 204,
  confusion_matrix: {
    labels: [0, 1],
    matrix: [
      [1, 0],
      [0, 1],
    ],
    tn: 1,
    fp: 0,
    fn: 0,
    tp: 1,
    convention: "",
  },
  metrics: [
    {
      name: "accuracy",
      label: "Accuracy",
      value: 0.8,
      numerator: 160,
      denominator: 200,
      undefined_reason: null,
      message: null,
      formula: "(TP+TN)/N",
      sample_size: 204,
    },
  ],
  groups: [],
  decision_engine: false,
};

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/audits/audit-1/threshold"]}>
        <Routes>
          <Route path="/audits/:auditId/threshold" element={<ThresholdPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("ThresholdPage mutateAsync error path", () => {
  beforeEach(() => {
    mutateAsync.mockReset();
    useAuditMock.mockReturnValue(gateEnabledAudit);
  });

  afterEach(() => {
    cleanup();
  });

  it("shows ErrorNote when the latest threshold request fails", async () => {
    mutateAsync.mockRejectedValue(new ApiError("Network down", 0));
    renderPage();
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent("Network down");
    });
  });

  it("clears a prior error when a later mutate succeeds", async () => {
    mutateAsync.mockRejectedValueOnce(new ApiError("First failed", 503)).mockResolvedValueOnce(successPayload);

    renderPage();
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("First failed"));

    fireEvent.change(screen.getByTestId("threshold-value"), { target: { value: "0.6" } });
    await waitFor(() => {
      expect(screen.queryByRole("alert")).not.toBeInTheDocument();
      expect(screen.getByTestId("threshold-results")).toBeInTheDocument();
    });
  });

  it("exposes methodology version and null≠0 copy", async () => {
    mutateAsync.mockResolvedValue({ ...successPayload, threshold: 0.5, metrics: [] });
    renderPage();
    await waitFor(() => {
      expect(screen.getByTestId("methodology-version")).toHaveTextContent("0.1.0");
    });
    expect(screen.getByTestId("null-not-zero")).toHaveTextContent(/not zeros/i);
  });
});
