import json
import time
from typing import List

from config import TestConfig, RequestResult
from metrics import TestMetrics


def build_export_payload(
    config: TestConfig,
    results: List[RequestResult],
    metrics: TestMetrics,
    wall_clock_seconds: float,
) -> dict:
    return {
        "config": {
            "provider": config.provider,
            "model": config.model,
            "concurrency": config.concurrency,
            "total_requests": config.total_requests,
            "stream": config.stream,
            "ramp_up": config.ramp_up,
            "ramp_up_delay": config.ramp_up_delay,
            "timeout": config.timeout,
            "save_responses": config.save_responses,
            "prompt": config.prompt,
        },
        "wall_clock_seconds": round(wall_clock_seconds, 3),
        "metrics": metrics.to_dict(),
        "results": [
            {
                "request_id": r.request_id,
                "status": r.status.value,
                "status_code": r.status_code,
                "ttft_ms": round(r.ttft_ms, 2) if r.ttft_ms is not None else None,
                "total_ms": round(r.total_ms, 2) if r.total_ms is not None else None,
                "token_count": r.token_count,
                "error_message": r.error_message,
                **({"output_text": r.output_text} if config.save_responses else {}),
            }
            for r in sorted(results, key=lambda x: x.request_id)
        ],
        "exported_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }


def save_run_to_json(
    config: TestConfig,
    results: List[RequestResult],
    metrics: TestMetrics,
    wall_clock_seconds: float,
    filepath: str,
) -> None:
    payload = build_export_payload(config, results, metrics, wall_clock_seconds)
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
