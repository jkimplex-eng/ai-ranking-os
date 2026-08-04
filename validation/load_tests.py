from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from time import perf_counter
from typing import Any


def run_load_test(
    operation: Callable[[int], Any],
    *,
    requests: int = 20,
    concurrency: int = 4,
) -> dict[str, float | int]:
    started = perf_counter()
    failures = 0
    with ThreadPoolExecutor(max_workers=concurrency, thread_name_prefix="pipeline-load") as pool:
        futures = [pool.submit(operation, index) for index in range(requests)]
        for future in as_completed(futures):
            try:
                future.result()
            except Exception:
                failures += 1
    duration = perf_counter() - started
    return {
        "requests": requests,
        "concurrency": concurrency,
        "failures": failures,
        "success_rate": round((requests - failures) / requests, 4),
        "duration_seconds": round(duration, 4),
        "throughput_per_second": round(requests / duration, 2) if duration else 0.0,
    }

