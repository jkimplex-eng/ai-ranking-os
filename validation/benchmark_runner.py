import statistics
from collections.abc import Callable
from time import perf_counter
from typing import Any


def percentile(values: list[float], percentile_value: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = min(len(ordered) - 1, int((len(ordered) - 1) * percentile_value))
    return ordered[index]


def run_benchmark(
    operation: Callable[[], Any],
    *,
    iterations: int = 25,
) -> dict[str, float | int]:
    latencies = []
    for _ in range(iterations):
        started = perf_counter()
        operation()
        latencies.append((perf_counter() - started) * 1000)
    total_seconds = sum(latencies) / 1000
    return {
        "iterations": iterations,
        "p50_ms": round(statistics.median(latencies), 3),
        "p95_ms": round(percentile(latencies, 0.95), 3),
        "p99_ms": round(percentile(latencies, 0.99), 3),
        "throughput_per_second": round(iterations / total_seconds, 2)
        if total_seconds
        else 0.0,
    }

