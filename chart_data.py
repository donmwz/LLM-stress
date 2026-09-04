from typing import List, Dict, Any
import pandas as pd

from config import RequestResult, RequestStatus


def build_timeline_df(results: List[RequestResult], run_start_perf: float) -> pd.DataFrame:
    """
    'Eşzamanlı İstek Yanıt Grafiği' için: her isteğin başlangıç offseti (sn)
    ve tamamlanma süresi (ms). X ekseni zaman, Y ekseni yanıt süresi.
    """
    rows = []
    for r in sorted(results, key=lambda x: x.request_id):
        if r.t0 is None:
            continue
        rows.append({
            "request_id": r.request_id,
            "start_offset_s": r.t0 - run_start_perf,
            "duration_ms": r.total_ms if r.total_ms is not None else 0,
            "ttft_ms": r.ttft_ms if r.ttft_ms is not None else None,
            "status": r.status.value,
        })
    return pd.DataFrame(rows)


def build_throughput_df(results: List[RequestResult], run_start_perf: float) -> pd.DataFrame:
    """
    Throughput (RPS): saniye bazlı bucket'larda tamamlanan istek sayısı.
    """
    buckets: Dict[int, int] = {}
    for r in results:
        if r.status != RequestStatus.SUCCESS or r.t2 is None:
            continue
        bucket = int(r.t2 - run_start_perf)
        buckets[bucket] = buckets.get(bucket, 0) + 1

    if not buckets:
        return pd.DataFrame(columns=["second", "completed_requests"])

    max_bucket = max(buckets.keys())
    rows = [{"second": s, "completed_requests": buckets.get(s, 0)} for s in range(max_bucket + 1)]
    return pd.DataFrame(rows)


def build_comparison_df(runs: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Multi-Provider Karşılaştırma bar chart'ı için: her run'ın (provider+model)
    ortalama TTFT ve TPS değerleri.
    'runs' elemanları: {"label": str, "metrics": TestMetrics}
    """
    rows = []
    for run in runs:
        m = run["metrics"]
        rows.append({
            "label": run["label"],
            "avg_ttft_ms": m.avg_ttft_ms or 0,
            "avg_tps": m.avg_tps or 0,
            "success_rate_pct": m.success_rate_pct,
        })
    return pd.DataFrame(rows)
