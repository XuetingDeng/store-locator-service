from collections import defaultdict, deque
from time import time

from fastapi import HTTPException, Request, Response, status


WINDOWS = (
    (60, 10, "minute"),
    (3600, 100, "hour"),
)

requests_by_ip: dict[str, dict[str, deque[float]]] = defaultdict(lambda: defaultdict(deque))


def client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def enforce_public_search_rate_limit(request: Request, response: Response) -> None:
    ip = client_ip(request)
    now = time()
    bucket = requests_by_ip[ip]

    remaining_values: list[int] = []
    for window_seconds, limit, label in WINDOWS:
        window = bucket[label]
        while window and window[0] <= now - window_seconds:
            window.popleft()

        remaining = limit - len(window)
        if remaining <= 0:
            retry_after = int(window_seconds - (now - window[0])) if window else window_seconds
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded",
                headers={
                    "Retry-After": str(max(retry_after, 1)),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Window": label,
                },
            )
        remaining_values.append(remaining - 1)

    for _, _, label in WINDOWS:
        bucket[label].append(now)

    response.headers["X-RateLimit-Limit-Minute"] = "10"
    response.headers["X-RateLimit-Remaining-Minute"] = str(remaining_values[0])
    response.headers["X-RateLimit-Limit-Hour"] = "100"
    response.headers["X-RateLimit-Remaining-Hour"] = str(remaining_values[1])
