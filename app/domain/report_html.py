"""Self-contained HTML audit report. Every figure is copied from the API payload."""

from __future__ import annotations

import html
from typing import Any


def _esc(value: object) -> str:
    if value is None:
        return "undefined"
    return html.escape(str(value))


def _num(value: object) -> str:
    if value is None:
        return "undefined"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.6g}"
    return html.escape(str(value))


def _fraction(metric: dict) -> str:
    if metric.get("numerator") is None or metric.get("denominator") is None:
        return ""
    return f" ({_num(metric['numerator'])}/{_num(metric['denominator'])})"


def _metric_rows(metrics: list[dict]) -> str:
    rows = []
    for metric in metrics:
        detail = _esc(metric.get("message") or "")
        rows.append(
            "<tr>"
            f"<td>{_esc(metric['label'])}</td>"
            f"<td>{_num(metric.get('value'))}{_fraction(metric)}</td>"
            f"<td>{_esc(metric['formula'])}</td>"
            f"<td>{detail}</td>"
            "</tr>"
        )
    return "".join(rows)


def render_report_html(document: dict[str, Any]) -> str:
    audit = document["audit"]
    provenance = audit.get("provenance") or {}
    confusion = audit.get("confusion_matrix") or {}
    parts = [
        "<!DOCTYPE html>",
        "<html lang='en'><head><meta charset='utf-8'>",
        "<title>FairHire Audit report</title>",
        "<style>",
        "body{font-family:Inter,Segoe UI,sans-serif;margin:0;background:#f4f6fb;color:#0f172a}",
        "main{max-width:980px;margin:0 auto;padding:32px 20px 64px}",
        "h1{font-size:32px;margin:0 0 8px}h2{font-size:20px;margin:32px 0 8px}",
        ".banner{background:#2563eb;color:#fff;padding:14px 20px;font-weight:600}",
        ".card{background:#fff;border:1px solid #e2e8f0;border-radius:12px;padding:16px;margin:12px 0}",
        "table{width:100%;border-collapse:collapse;font-size:14px}",
        "th,td{text-align:left;padding:8px;border-bottom:1px solid #e2e8f0;vertical-align:top}",
        ".warn{background:#fff7ed;border-color:#fdba74}",
        "</style></head><body>",
        "<div class='banner'>Audit record. Not a certificate of fairness, compliance, or fitness for use.</div>",
        "<main>",
        "<h1>FairHire Audit</h1>",
        f"<p>{_esc(document['statement'])}</p>",
        "<section class='card'>",
        "<h2>Provenance</h2><dl>",
    ]
    for key in (
        "dataset_name",
        "dataset_id",
        "is_synthetic",
        "synthetic_profile",
        "content_sha256",
        "row_count",
        "code_version",
        "git_sha",
        "fairlearn_version",
        "sklearn_version",
        "numpy_version",
        "scipy_version",
        "seed",
        "bootstrap_iterations",
        "bootstrap_iterations_requested",
        "bootstrap_capped",
        "bootstrap_method",
        "sampling_unit",
        "small_group_min_n",
        "positive_label",
        "score_semantics",
        "started_at",
        "finished_at",
    ):
        parts.append(f"<dt>{_esc(key)}</dt><dd>{_esc(provenance.get(key))}</dd>")
    parts.append("</dl></section>")
    if confusion:
        parts.append("<section class='card'><h2>Confusion matrix</h2>")
        parts.append(f"<p>{_esc(confusion.get('convention'))}</p>")
        parts.append(
            "<table><tr><th></th><th>Predicted 0</th><th>Predicted 1</th></tr>"
            f"<tr><th>Actual 0</th><td>TN {_num(confusion.get('tn'))}</td>"
            f"<td>FP {_num(confusion.get('fp'))}</td></tr>"
            f"<tr><th>Actual 1</th><td>FN {_num(confusion.get('fn'))}</td>"
            f"<td>TP {_num(confusion.get('tp'))}</td></tr></table></section>"
        )
    parts.append("<section class='card'><h2>Overall metrics</h2><table>")
    parts.append("<tr><th>Metric</th><th>Value</th><th>Formula</th><th>Note</th></tr>")
    parts.append(_metric_rows(audit.get("metrics") or []))
    parts.append("</table></section>")
    for column in audit.get("groups") or []:
        parts.append(f"<section class='card'><h2>Groups: {_esc(column['column'])}</h2>")
        for group in column["groups"]:
            parts.append(f"<h3>{_esc(group['group_value'])} (n={_num(group['sample_size'])})</h3>")
            if group["suppressed"]:
                parts.append(f"<p>{_esc(group.get('message'))}</p>")
                continue
            parts.append("<table><tr><th>Metric</th><th>Value</th><th>Formula</th><th>Note</th></tr>")
            parts.append(_metric_rows(group["metrics"]))
            parts.append("</table>")
        parts.append("<h3>Differences</h3><ul>")
        for item in column["disparities"]:
            parts.append(
                "<li>"
                f"{_esc(item['label'])}: {_num(item.get('value'))}. "
                f"{_esc(item['formula'])} "
                f"Included: {_esc(', '.join(item['groups_included']) or 'none')}. "
                f"Excluded: {_esc(', '.join(item['groups_excluded']) or 'none')}. "
                f"{_esc(item.get('message') or '')}"
                "</li>"
            )
        parts.append("</ul></section>")
    gate = audit.get("score_gate") or {}
    parts.append("<section class='card'><h2>Score gate</h2>")
    parts.append(f"<p>Enabled: {_esc(gate.get('enabled'))}. Calibrated claim: false.</p>")
    parts.append(f"<p>{_esc(gate.get('reason'))}</p>")
    if gate.get("brier_score") is not None:
        parts.append(f"<p>Brier score: {_num(gate.get('brier_score'))}. {_esc(gate.get('brier_formula'))}</p>")
    parts.append("</section>")
    parts.append("<section class='card warn'><h2>What this cannot conclude</h2><ul>")
    for line in audit.get("cannot_conclude") or []:
        parts.append(f"<li>{_esc(line)}</li>")
    parts.append("</ul></section>")
    parts.append("<section class='card'><h2>Assumptions</h2><ul>")
    for line in audit.get("assumptions") or []:
        parts.append(f"<li>{_esc(line)}</li>")
    parts.append("</ul></section>")
    parts.append("<section class='card'><h2>Warnings</h2><ul>")
    for line in audit.get("warnings") or []:
        parts.append(f"<li>{_esc(line)}</li>")
    if not audit.get("warnings"):
        parts.append("<li>None recorded.</li>")
    parts.append("</ul></section></main></body></html>")
    return "".join(parts)
