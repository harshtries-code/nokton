import time
import random
from typing import Any


class APIError(Exception):
    pass


class RateLimitError(APIError):
    pass


class QuotaExceededError(APIError):
    pass


class AuthError(APIError):
    pass


class TimeoutError(APIError):
    pass


class ServerError(APIError):
    pass


class InvalidRequestError(APIError):
    pass


class ContextLengthError(APIError):
    pass


class EmptyResponseError(APIError):
    pass


def classify_api_error(exception: str | Exception, status_code: int | None = None) -> APIError:
    err_str = str(exception).lower() if not isinstance(exception, str) else exception.lower()

    if status_code == 429 or "rate_limit" in err_str or "rate limit" in err_str:
        return RateLimitError(str(exception))
    if status_code == 402 or "quota" in err_str or "insufficient_quota" in err_str:
        return QuotaExceededError(str(exception))
    if status_code in (401, 403) or "auth" in err_str or "unauthorized" in err_str or "forbidden" in err_str:
        return AuthError(str(exception))
    if status_code == 408 or status_code == 504 or "timeout" in err_str or "timed out" in err_str:
        return TimeoutError(str(exception))
    if status_code == 413 or "context_length" in err_str or "too long" in err_str or "maximum context" in err_str:
        return ContextLengthError(str(exception))
    if status_code in (400, 422) or "invalid" in err_str or "bad request" in err_str:
        return InvalidRequestError(str(exception))
    if status_code in (500, 502, 503) or "server_error" in err_str or "server error" in err_str or "service unavailable" in err_str:
        return ServerError(str(exception))
    if not exception or str(exception).strip() == "":
        return EmptyResponseError("Empty or null response")
    return APIError(str(exception))


class RetryStrategy:
    STRATEGIES: dict[type[APIError], dict[str, Any]] = {
        RateLimitError: {"retry": True, "backoff": "exponential", "base_s": 5, "max_s": 120, "jitter": True},
        QuotaExceededError: {"retry": False, "fallback": True},
        AuthError: {"retry": False, "fallback": True},
        TimeoutError: {"retry": True, "backoff": "linear", "base_s": 2, "max_s": 30, "jitter": False},
        ServerError: {"retry": True, "backoff": "exponential", "base_s": 2, "max_s": 60, "jitter": True},
        ContextLengthError: {"retry": False, "fallback": False},
        InvalidRequestError: {"retry": False, "fallback": False},
        EmptyResponseError: {"retry": True, "backoff": "linear", "base_s": 1, "max_s": 10, "jitter": False},
        APIError: {"retry": True, "backoff": "exponential", "base_s": 3, "max_s": 60, "jitter": True},
    }

    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries

    def get_strategy(self, error: APIError) -> dict[str, Any]:
        for err_type, strategy in self.STRATEGIES.items():
            if isinstance(error, err_type):
                return strategy
        return self.STRATEGIES[APIError]

    def should_retry(self, error: APIError, attempt: int) -> bool:
        strategy = self.get_strategy(error)
        if not strategy.get("retry", False):
            return False
        return attempt < self.max_retries

    def should_fallback(self, error: APIError) -> bool:
        strategy = self.get_strategy(error)
        return strategy.get("fallback", True)

    def delay(self, error: APIError, attempt: int) -> float:
        strategy = self.get_strategy(error)
        backoff = strategy.get("backoff", "exponential")
        base_s = strategy.get("base_s", 3)
        max_s = strategy.get("max_s", 60)
        jitter = strategy.get("jitter", True)

        if backoff == "exponential":
            d = min(base_s * (2 ** attempt), max_s)
        else:
            d = min(base_s * (attempt + 1), max_s)

        if jitter:
            d = d * (0.5 + random.random() * 0.5)
        return d

    def wait(self, error: APIError, attempt: int):
        d = self.delay(error, attempt)
        time.sleep(d)
        return d
