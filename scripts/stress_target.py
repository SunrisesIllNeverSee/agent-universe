"""Resolve stress-test targets without performing network requests."""
from urllib.parse import urlsplit


def stress_target(environ) -> str:
    target = environ.get("CIVITAE_URL", "http://127.0.0.1:8300")
    parsed = urlsplit(target)
    if (
        parsed.scheme not in ("http", "https")
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("CIVITAE_URL must be an HTTP(S) URL without credentials, query or fragment")
    if parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
        if environ.get("CIVITAE_STRESS_ALLOW_REMOTE") != "1":
            raise ValueError(
                "Remote stress testing requires explicit CIVITAE_URL and "
                "CIVITAE_STRESS_ALLOW_REMOTE=1; this suite creates persistent data"
            )
    return target.rstrip("/")
