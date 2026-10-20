export function formatRate(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  return `${(value * 100).toFixed(1)}%`;
}

export function formatCount(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "—";
  }
  if (Number.isInteger(value)) {
    return String(value);
  }
  return value.toFixed(2);
}

export function formatInterval(lower: number | null, upper: number | null): string {
  if (lower === null || upper === null) {
    return "—";
  }
  return `${formatRate(lower)} – ${formatRate(upper)}`;
}
