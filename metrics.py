import statistics
from dataclasses import dataclass, asdict
from typing import List, Optional

from config import RequestResult, RequestStatus


@dataclass
class TestMetrics:
    total_requests: int
    success_count: int
    error_count: int
    rate_limited_count: int
    timeout_count: int
    success_rate_pct: float

    min_total_ms: Optional[float]
    max_total_ms: Optional[float]
    avg_total_ms: Optional[float]

    p50_ms: Optional[float]
    p90_ms: Optional[float]
    p99_ms: Optional[float]

    avg_ttft_ms: Optional[float]

    total_tokens: int
    avg_tps: Optional[float]        # istek-başına tokens/süre değerlerinin ortalaması
    aggregate_tps: Optional[float]  # toplam token / toplam duvar-saati süresi (gerçek throughput)

    def to_dict(self) -> dict:
        return asdict(self)


def _percentile(sorted_values: List[float], pct: float) -> Optional[float]:
    if not sorted_values:
        return None
    if len(sorted_values) == 1:
        return sorted_values[0]
    k = (len(sorted_values) - 1) * (pct / 100)
    f = int(k)
    c = min(f + 1, len(sorted_values) - 1)
    if f == c:
        return sorted_values[f]
    return sorted_values[f] + (sorted_values[c] - sorted_values[f]) * (k - f)


def compute_metrics(
    results: List[RequestResult], wall_clock_seconds: Optional[float] = None
) -> TestMetrics:
    total = len(results)
    success = [r for r in results if r.status == RequestStatus.SUCCESS]
    errors = [r for r in results if r.status == RequestStatus.ERROR]
    rate_limited = [r for r in results if r.status == RequestStatus.RATE_LIMITED]
    timeouts = [r for r in results if r.status == RequestStatus.TIMEOUT]

    total_times = sorted(r.total_ms for r in success if r.total_ms is not None)
    ttfts = [r.ttft_ms for r in success if r.ttft_ms is not None]
    total_tokens = sum(r.token_count or 0 for r in success)

    per_request_tps = []
    for r in success:
        if r.token_count and r.total_ms and r.total_ms > 0:
            per_request_tps.append(r.token_count / (r.total_ms / 1000))

    aggregate_tps = (
        total_tokens / wall_clock_seconds
        if wall_clock_seconds and wall_clock_seconds > 0
        else None
    )

    return TestMetrics(
        total_requests=total,
        success_count=len(success),
        error_count=len(errors),
        rate_limited_count=len(rate_limited),
        timeout_count=len(timeouts),
        success_rate_pct=round((len(success) / total * 100), 2) if total else 0.0,
        min_total_ms=min(total_times) if total_times else None,
        max_total_ms=max(total_times) if total_times else None,
        avg_total_ms=statistics.mean(total_times) if total_times else None,
        p50_ms=_percentile(total_times, 50),
        p90_ms=_percentile(total_times, 90),
        p99_ms=_percentile(total_times, 99),
        avg_ttft_ms=statistics.mean(ttfts) if ttfts else None,
        total_tokens=total_tokens,
        avg_tps=statistics.mean(per_request_tps) if per_request_tps else None,
        aggregate_tps=aggregate_tps,
    )
