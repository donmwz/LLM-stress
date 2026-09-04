import csv
import io
from typing import List

from config import TestConfig, RequestResult
from metrics import TestMetrics
from logger import build_export_payload


def export_to_csv_string(
    config: TestConfig,
    results: List[RequestResult],
    metrics: TestMetrics,
    wall_clock_seconds: float,
) -> str:
    """İstek bazlı sonuçları CSV metni olarak döndürür (dosyaya değil - Streamlit
    download_button'a doğrudan verilebilsin diye)."""
    payload = build_export_payload(config, results, metrics, wall_clock_seconds)
    buffer = io.StringIO()
    fieldnames = ["request_id", "status", "status_code", "ttft_ms", "total_ms",
                  "token_count", "error_message"]
    if config.save_responses:
        fieldnames.append("output_text")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in payload["results"]:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    return buffer.getvalue()


def export_to_csv_file(
    config: TestConfig,
    results: List[RequestResult],
    metrics: TestMetrics,
    wall_clock_seconds: float,
    filepath: str,
) -> None:
    csv_text = export_to_csv_string(config, results, metrics, wall_clock_seconds)
    with open(filepath, "w", encoding="utf-8", newline="") as f:
        f.write(csv_text)


_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="utf-8">
<title>LLM Stress Test Raporu</title>
<style>
  body {{ font-family: -apple-system, Arial, sans-serif; margin: 40px; color: #1a1a2e; }}
  h1 {{ color: #16213e; }}
  table {{ border-collapse: collapse; width: 100%; margin-bottom: 24px; }}
  th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; font-size: 14px; }}
  th {{ background: #16213e; color: white; }}
  tr:nth-child(even) {{ background: #f4f6fb; }}
  .summary-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 24px; }}
  .card {{ background: #f4f6fb; border-radius: 8px; padding: 14px; text-align: center; }}
  .card .value {{ font-size: 22px; font-weight: 700; color: #16213e; }}
  .card .label {{ font-size: 12px; color: #555; text-transform: uppercase; }}
  .status-success {{ color: #1a7f37; font-weight: 600; }}
  .status-error, .status-timeout {{ color: #b3261e; font-weight: 600; }}
  .status-rate_limited {{ color: #b06a00; font-weight: 600; }}
</style>
</head>
<body>
  <h1>LLM Stress Test Raporu</h1>
  <p><b>Provider:</b> {provider} &nbsp;|&nbsp; <b>Model:</b> {model} &nbsp;|&nbsp;
     <b>Concurrency:</b> {concurrency} &nbsp;|&nbsp; <b>Toplam İstek:</b> {total_requests} &nbsp;|&nbsp;
     <b>Süre:</b> {wall_clock_seconds:.2f}s</p>

  <div class="summary-grid">
    <div class="card"><div class="value">{success_rate_pct}%</div><div class="label">Success Rate</div></div>
    <div class="card"><div class="value">{avg_total_ms:.0f} ms</div><div class="label">Ort. Süre</div></div>
    <div class="card"><div class="value">{p99_ms:.0f} ms</div><div class="label">P99 Latency</div></div>
    <div class="card"><div class="value">{aggregate_tps:.1f}</div><div class="label">TPS (agg)</div></div>
  </div>

  <h2>Detaylı Metrikler</h2>
  <table>
    <tr><th>Metrik</th><th>Değer</th></tr>
    <tr><td>Toplam istek</td><td>{total_requests}</td></tr>
    <tr><td>Başarılı</td><td>{success_count}</td></tr>
    <tr><td>Hata</td><td>{error_count}</td></tr>
    <tr><td>Rate limited (429)</td><td>{rate_limited_count}</td></tr>
    <tr><td>Timeout</td><td>{timeout_count}</td></tr>
    <tr><td>Min / Max / Avg süre (ms)</td><td>{min_total_ms:.0f} / {max_total_ms:.0f} / {avg_total_ms:.0f}</td></tr>
    <tr><td>P50 / P90 / P99 (ms)</td><td>{p50_ms:.0f} / {p90_ms:.0f} / {p99_ms:.0f}</td></tr>
    <tr><td>Ortalama TTFT (ms)</td><td>{avg_ttft_ms:.0f}</td></tr>
    <tr><td>Toplam token</td><td>{total_tokens}</td></tr>
    <tr><td>TPS (istek-başı ort. / agregatif)</td><td>{avg_tps:.1f} / {aggregate_tps:.1f}</td></tr>
  </table>

  <h2>İstek Bazlı Sonuçlar</h2>
  <table>
    <tr><th>#</th><th>Durum</th><th>HTTP</th><th>TTFT (ms)</th><th>Toplam (ms)</th><th>Token</th><th>Hata</th></tr>
    {rows_html}
  </table>
</body>
</html>
"""


def export_to_html_string(
    config: TestConfig,
    results: List[RequestResult],
    metrics: TestMetrics,
    wall_clock_seconds: float,
) -> str:
    payload = build_export_payload(config, results, metrics, wall_clock_seconds)
    m = payload["metrics"]

    row_lines = []
    for r in payload["results"]:
        row_lines.append(
            f"<tr><td>{r['request_id']}</td>"
            f"<td class='status-{r['status']}'>{r['status']}</td>"
            f"<td>{r['status_code'] or '-'}</td>"
            f"<td>{r['ttft_ms'] if r['ttft_ms'] is not None else '-'}</td>"
            f"<td>{r['total_ms'] if r['total_ms'] is not None else '-'}</td>"
            f"<td>{r['token_count'] or 0}</td>"
            f"<td>{(r['error_message'] or '')[:80]}</td></tr>"
        )

    return _HTML_TEMPLATE.format(
        provider=config.provider,
        model=config.model,
        concurrency=config.concurrency,
        total_requests=m["total_requests"],
        wall_clock_seconds=wall_clock_seconds,
        success_rate_pct=m["success_rate_pct"],
        avg_total_ms=m["avg_total_ms"] or 0,
        p99_ms=m["p99_ms"] or 0,
        aggregate_tps=m["aggregate_tps"] or 0,
        success_count=m["success_count"],
        error_count=m["error_count"],
        rate_limited_count=m["rate_limited_count"],
        timeout_count=m["timeout_count"],
        min_total_ms=m["min_total_ms"] or 0,
        max_total_ms=m["max_total_ms"] or 0,
        p50_ms=m["p50_ms"] or 0,
        p90_ms=m["p90_ms"] or 0,
        avg_ttft_ms=m["avg_ttft_ms"] or 0,
        total_tokens=m["total_tokens"],
        avg_tps=m["avg_tps"] or 0,
        rows_html="\n    ".join(row_lines),
    )


def export_to_html_file(
    config: TestConfig,
    results: List[RequestResult],
    metrics: TestMetrics,
    wall_clock_seconds: float,
    filepath: str,
) -> None:
    html = export_to_html_string(config, results, metrics, wall_clock_seconds)
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
