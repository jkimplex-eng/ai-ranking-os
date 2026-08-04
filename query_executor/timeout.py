from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeoutError


class ProviderTimeoutError(TimeoutError):
    """Provider step exceeded its timeout."""


def run_with_timeout[T](operation: Callable[[], T], timeout_seconds: float) -> T:
    pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="provider-timeout")
    future = pool.submit(operation)
    try:
        return future.result(timeout=timeout_seconds)
    except FutureTimeoutError as error:
        future.cancel()
        raise ProviderTimeoutError(
            f"Provider timed out after {timeout_seconds:g} seconds"
        ) from error
    finally:
        pool.shutdown(wait=False, cancel_futures=True)
