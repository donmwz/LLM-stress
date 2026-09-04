import argparse
import asyncio
import os

from dotenv import load_dotenv

from config import TestConfig, RequestStatus
from engine import AsyncEngine
from metrics import compute_metrics
from logger import save_run_to_json


def parse_args():
    load_dotenv()
    p = argparse.ArgumentParser(description="LLM Stress Tester - FAZ 1")
    p.add_argument("--provider", required=True, choices=["openrouter", "openai", "anthropic", "gemini", "grok"])
    p.add_argument("--api-key", default=None, help="OpenRouter için OPENROUTER_API_KEY otomatik kullanılır")
    p.add_argument("--model", default=None, help="OpenRouter için OPENROUTER_MODEL veya openrouter/free kullanılır")
    p.add_argument("--prompt", required=True)
    p.add_argument("--concurrency", type=int, default=5)
    p.add_argument("--total", type=int, default=20)
    p.add_argument("--timeout", type=float, default=60.0)
    p.add_argument("--ramp-up", action="store_true")
    p.add_argument("--ramp-up-delay", type=float, default=0.5)
    p.add_argument("--no-stream", action="store_true")
    p.add_argument("--save-responses", action="store_true")
    p.add_argument("--output", default=None, help="Sonuçları JSON olarak kaydedeceğin dosya yolu (örn. sonuc.json)")
    args = p.parse_args()

    if args.provider == "openrouter":
        args.api_key = args.api_key or os.getenv("OPENROUTER_API_KEY")
        args.model = args.model or os.getenv("OPENROUTER_MODEL", "openrouter/free")
    if not args.api_key or not args.model:
        p.error("API anahtarı ve model gerekli. OpenRouter için .env değişkenlerini kontrol edin.")

    config = TestConfig(
        provider=args.provider,
        api_key=args.api_key,
        model=args.model,
        prompt=args.prompt,
        concurrency=args.concurrency,
        total_requests=args.total,
        timeout=args.timeout,
        ramp_up=args.ramp_up,
        ramp_up_delay=args.ramp_up_delay,
        stream=not args.no_stream,
        save_responses=args.save_responses,
    )
    return config, args.output


async def main():
    config, output_path = parse_args()
    engine = AsyncEngine(config)

    print(f"[+] Test başlıyor: provider={config.provider}, model={config.model}, "
          f"concurrency={config.concurrency}, total={config.total_requests}, "
          f"stream={config.stream}, ramp_up={config.ramp_up}")

    results = await engine.run()
    m = compute_metrics(results, wall_clock_seconds=engine.wall_clock_seconds)

    print(f"\n[+] Tamamlandı ({engine.wall_clock_seconds:.2f}s duvar-saati)")
    print(f"    Success Rate     : {m.success_rate_pct}%  ({m.success_count}/{m.total_requests})")
    print(f"    Hatalar          : error={m.error_count}, rate_limited(429)={m.rate_limited_count}, timeout={m.timeout_count}")
    print(f"    Süre (min/avg/max): {m.min_total_ms:.0f} / {m.avg_total_ms:.0f} / {m.max_total_ms:.0f} ms" if m.avg_total_ms else "    Süre             : -")
    print(f"    P50 / P90 / P99  : {m.p50_ms:.0f} / {m.p90_ms:.0f} / {m.p99_ms:.0f} ms" if m.p50_ms else "    Percentile       : -")
    print(f"    Ortalama TTFT    : {m.avg_ttft_ms:.0f} ms" if m.avg_ttft_ms else "    Ortalama TTFT    : -")
    print(f"    Toplam token     : {m.total_tokens}")
    print(f"    TPS (avg / agg)  : {m.avg_tps:.1f} / {m.aggregate_tps:.1f}" if m.avg_tps and m.aggregate_tps else "    TPS              : -")

    print()
    for r in sorted(results, key=lambda x: x.request_id):
        ttft = f"{r.ttft_ms:.0f}ms" if r.ttft_ms is not None else "-"
        total = f"{r.total_ms:.0f}ms" if r.total_ms is not None else "-"
        print(f"  #{r.request_id:>3} | {r.status.value:<13} | TTFT={ttft:<8} | "
              f"total={total:<8} | tokens={r.token_count}")

    if output_path:
        save_run_to_json(config, results, m, engine.wall_clock_seconds, output_path)
        print(f"\n[+] Sonuçlar kaydedildi: {output_path}")


if __name__ == "__main__":
    asyncio.run(main())
