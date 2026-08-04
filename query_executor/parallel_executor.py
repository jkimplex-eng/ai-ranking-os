from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed


def execute_parallel[T, R](
    items: list[T],
    operation: Callable[[T], R],
    *,
    max_workers: int = 8,
) -> list[R]:
    results: dict[int, R] = {}
    with ThreadPoolExecutor(
        max_workers=min(max_workers, len(items)),
        thread_name_prefix="query-executor",
    ) as pool:
        futures = {pool.submit(operation, item): index for index, item in enumerate(items)}
        for future in as_completed(futures):
            results[futures[future]] = future.result()
    return [results[index] for index in range(len(items))]
