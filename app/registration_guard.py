"""Cross-route signup coordination for the single-worker CIVITAE deployment.

Callers must hold REGISTRATION_LOCK across registry reload, check, append, persist.
This is process-local; production must remain one worker until an atomic
multi-process backing store replaces the JSON registry.
"""
from threading import RLock

REGISTRATION_LOCK = RLock()
MAX_AGENTS_PER_IP = 3


def origin_has_capacity(registry: list[dict], source_ip: str | None) -> bool:
    # Some direct MCP/unit-test calls have no observable ingress origin. The
    # shared global cap still applies; never treat "unknown" as a trusted user.
    if not source_ip or source_ip in ("unknown", "testclient"):
        return True
    return sum(1 for agent in registry if agent.get("type") == "agent" and
               agent.get("signup_ip") == source_ip) < MAX_AGENTS_PER_IP
