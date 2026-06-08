import re
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

PROMPT_INJECTION_PATTERNS = [
    r"ignore\s+(?:all\s+)?(?:previous\s+)?instructions",
    r"bypass\s+(?:the\s+)?system",
    r"override\s+(?:the\s+)?instructions",
    r"you\s+are\s+now\s+(?:a|in)\b",
    r"developer\s+mode",
]

HARMFUL_PATTERNS = [
    r"\bself[- ]harm\b",
    r"\bsuicide\b",
    r"\bhow\s+to\s+build\s+a\s+bomb\b",
    r"\bhate\s+speech\b",
    r"\bmake\s+weapons\b",
    r"\bchild\s+abuse\b",
]

def sanitize_and_check_prompt(prompt: str) -> str:
    """Scan prompt for injection and safety moderation patterns, and strip potential HTML tags."""
    # Strip HTML tags
    cleaned = re.sub(r"<[^>]*>", "", prompt)
    
    # Check injection keywords
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            raise ValueError("Potential prompt injection detected. Request blocked for security.")
            
    # Check safety moderation keywords
    for pattern in HARMFUL_PATTERNS:
        if re.search(pattern, cleaned, re.IGNORECASE):
            raise ValueError("Potential safety violation detected. Request blocked for safety.")
            
    return cleaned.strip()


class RateLimitMiddleware:
    """Simple in-memory rate-limiter middleware (120 reqs/min) using pure ASGI."""
    
    def __init__(self, app, limit_per_minute: int = 120):
        self.app = app
        self.limit_per_minute = limit_per_minute
        self.requests = {}

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # Bypass preflight OPTIONS requests
        if scope.get("method") == "OPTIONS":
            await self.app(scope, receive, send)
            return

        # Skip rate limit for docs, health, etc.
        path = scope.get("path", "")
        if path.startswith("/docs") or path.startswith("/openapi") or path.startswith("/api/health"):
            await self.app(scope, receive, send)
            return

        # Retrieve client IP or auth token as identifier
        client = scope.get("client")
        client_key = client[0] if client else "unknown"

        # Look for authorization header
        for name, value in scope.get("headers", []):
            if name == b"authorization":
                val_str = value.decode("latin1")
                if val_str.startswith("Bearer "):
                    client_key = val_str
                    break

        now = time.time()
        
        if client_key not in self.requests:
            self.requests[client_key] = []
            
        # Filter timestamps within the last 60 seconds
        self.requests[client_key] = [t for t in self.requests[client_key] if now - t < 60]

        if len(self.requests[client_key]) >= self.limit_per_minute:
            response_body = b'{"detail":"Too many requests. Please try again in a minute."}'
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"access-control-allow-origin", b"*"),
                ]
            })
            await send({
                "type": "http.response.body",
                "body": response_body,
            })
            return

        self.requests[client_key].append(now)
        await self.app(scope, receive, send)
