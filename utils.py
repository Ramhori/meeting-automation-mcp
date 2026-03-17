import asyncio
import logging

from models import ServiceResult

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {429, 500, 502, 503}
MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = [1, 3, 5]


async def with_retry(func, *args, **kwargs) -> ServiceResult:
    """Retry wrapper for service calls with exponential backoff."""
    result = None
    for attempt in range(MAX_RETRIES):
        result = await func(*args, **kwargs)
        if result.success:
            return result
        if not result.recoverable:
            return result
        if attempt < MAX_RETRIES - 1:
            delay = DEFAULT_RETRY_DELAY[attempt]
            if (
                result.error_code == "RATE_LIMIT"
                and result.data
                and "retry_after" in result.data
            ):
                delay = result.data["retry_after"]
            await asyncio.sleep(delay)
            logger.warning(
                "Retry %d/%d: %s", attempt + 2, MAX_RETRIES, result.error_message
            )
    return result
