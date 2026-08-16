import logging
import time

logger = logging.getLogger("apps.core.request")


class RequestLoggingMiddleware:
    """Logs method, path, status code and duration for every request.

    Kept intentionally lightweight so it has negligible overhead under
    high traffic; heavier diagnostics should use APM tooling instead.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        start = time.monotonic()
        response = self.get_response(request)
        duration_ms = (time.monotonic() - start) * 1000
        logger.info(
            "%s %s -> %s (%.2fms) user=%s",
            request.method,
            request.get_full_path(),
            response.status_code,
            duration_ms,
            getattr(request.user, "email", "anonymous") if hasattr(request, "user") else "n/a",
        )
        return response
