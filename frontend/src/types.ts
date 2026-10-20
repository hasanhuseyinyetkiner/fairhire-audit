export interface Metric {
  name: string;
  label: string;
  value: number | null;
  numerator: number | null;
  denominator: number | null;
  undefined_reason: string | null;
  message: string | null;
  formula: string;
  sample_size: number | null;
}

export interface Confusion {
  labels: number[];
  matrix: number[][];
  tn: number;
  fp: number;
  fn: number;
  tp: number;
  convention: string;
}

export interface ConfidenceInterval {
  metric_name: string;
  label: string;
  group_column: string | null;
  group_value: string | null;
  point: number | null;
  lower: number | null;
  upper: number | null;
  iterations: number;
  iterations_requested: number;
  capped: boolean;
  valid_replicates: number;
  seed: number;
  method: string;
  sampling_unit: string;
  confidence: string;
  undefined_reason: string | null;
  message: string | null;
}

export interface GroupBlock {
  group_column: string;
  group_value: string;
  sample_size: number;
  suppressed: boolean;
  suppression_reason: string | null;
  message: string | null;
  metrics: Metric[];
}

export interface Disparity {
  name: string;
  label: string;
  value: number | null;
  undefined_reason: string | null;
  message: string | null;
  formula: string;
  method: string;
  groups_included: string[];
  groups_excluded: string[];
}

export interface GroupColumn {
  column: string;
  intersection: boolean;
  groups: GroupBlock[];
  disparities: Disparity[];
}

export interface ReliabilityBin {
  bin_start: number;
  bin_end: number;
  count: number;
  mean_predicted: number | null;
  observed_rate: number | null;
  undefined_reason: string | null;
  message: string | null;
  small_bin: boolean;
}

export interface ScoreGate {
  enabled: boolean;
  semantics: string | null;
  reason: string;
  brier_score: number | null;
  brier_formula: string;
  reliability: ReliabilityBin[] | null;
  calibrated: boolean;
}

export interface ComparisonDelta {
  name: string;
  label: string;
  primary: number | null;
  alternate: number | null;
  delta: number | null;
  undefined_reason: string | null;
  message: string | null;
  formula: string;
}

export interface Comparison {
  available: boolean;
  reason: string;
  metrics: Metric[];
  deltas: ComparisonDelta[];
}

export interface Provenance {
  dataset_id: string;
  dataset_name: string;
  is_synthetic: boolean;
  synthetic_profile: string | null;
  content_sha256: string;
  row_count: number;
  code_version: string;
  git_sha: string | null;
  fairlearn_version: string;
  sklearn_version: string;
  numpy_version: string;
  scipy_version: string;
  pandas_version: string;
  seed: number;
  bootstrap_iterations: number;
  bootstrap_iterations_requested: number;
  bootstrap_capped: boolean;
  bootstrap_method: string;
  sampling_unit: string;
  small_group_min_n: number;
  positive_label: string | null;
  score_semantics: string | null;
  mapping: Record<string, unknown>;
  started_at: string | null;
  finished_at: string | null;
}

export interface AuditPayload {
  id: string;
  dataset_id: string;
  status: string;
  failure_reason: string | null;
  failure_code: string | null;
  decision_engine: boolean;
  sample_size: number | null;
  confusion_matrix: Confusion | null;
  metrics: Metric[];
  comparison: Comparison | null;
  groups: GroupColumn[];
  confidence_intervals: ConfidenceInterval[];
  score_gate: ScoreGate | null;
  warnings: string[];
  assumptions: string[];
  cannot_conclude: string[];
  provenance: Provenance | null;
}

export interface Mapping {
  y_true: string;
  y_pred: string | null;
  y_pred_alt: string | null;
  score: string | null;
  score_semantics: "probability" | "ranking_score" | null;
  sensitive_columns: string[];
  sample_weight: string | null;
  timestamp_column: string | null;
  positive_label: string;
}

export interface DatasetSummary {
  id: string;
  name: string;
  source: string;
  synthetic_profile: string | null;
  is_synthetic: boolean;
  original_filename: string;
  content_sha256: string;
  row_count: number;
  column_names: string[];
  created_at: string;
  latest_audit_id: string | null;
  latest_audit_status: string | null;
  mapping: Mapping | null;
}

export interface Meta {
  name: string;
  version: string;
  app_env: string;
  demo: boolean;
  banner: string | null;
  fairlearn_version: string;
  decision_engine: boolean;
  bootstrap_cap: number;
  small_group_min_n: number;
  retention_days: number;
}

export interface Profile {
  id: string;
  title: string;
  description: string;
  row_count: number;
}

export interface ThresholdResult {
  id: string;
  audit_id: string;
  threshold: number;
  score_semantics: string;
  note: string;
  point_estimates_only: boolean;
  sample_size: number;
  confusion_matrix: Confusion;
  metrics: Metric[];
  groups: GroupColumn[];
  decision_engine: boolean;
}

export interface GroupView {
  audit_id: string;
  intersection: boolean;
  available: boolean;
  note: string;
  groups: GroupColumn[];
  cannot_conclude: string[];
}
