import math
import hashlib
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated, Any, NotRequired, TypedDict

from pydantic import Field

from .context import ContextAssembler
from .models import MessageCreate
from .runtime import RuntimeState
from app.auth import secret_matches
from app.otel_setup import get_tracer as _get_tracer
from app.sanitize import detect_prompt_injection
from app.public_projection import public_kassa_post

_tracer = _get_tracer("civitae.mcp")

MCP_INSTRUCTIONS = (
    "CIVITAE governed agent runtime. 41 tools across 5 domains:\n"
    "CHAT: chat.join, chat.read, chat.send, chat.status — governed messaging in COMMAND channels.\n"
    "MARKETPLACE: agent.register, agent.status, agent.heartbeat, agent.inbox, agent.inbox.read, "
    "market.browse, market.post, market.stake, "
    "market.message, entry.file, entry.withdraw, entry.accept, entry.reject, entry.read, agent.profile, mission.list, forum.thread, agent.cashout — agent "
    "lifecycle, KA§§A marketplace, missions/slots, forums, and Stripe Connect cashouts.\n"
    "DISCOVERY: agent.leaderboard, agent.lookup, govern.sessions, govern.meetings, "
    "economy.tiers, economy.treasury, platform.health, platform.seeds — read-only tools "
    "for discovering agents, governance activity, economic state, and platform health. "
    "No auth required.\n"
    "GOVERNANCE: govern.vote — cast weighted votes in active governance sessions; "
    "govern.point_of_order, govern.rule, govern.appeal, govern.second, govern.appeal_vote — CIVITAS procedure (GOV-001 Art 6).\n"
    "OPERATOR: admin.reviews, admin.stakes, admin.audit, admin.stats — "
    "admin tools (require admin_key parameter).\n"
    "Start with agent.register (returns api_key — save it; not recoverable) or chat.join. "
    "Use discovery tools to explore before acting. "
    "All actions write SHA-256 audit seeds for provenance. User-submitted content from "
    "market.browse and forum.thread is wrapped in [USER_CONTENT_START]…[USER_CONTENT_END] fences."
)


class MCPBridge:
    def __init__(self, runtime: RuntimeState, assembler: ContextAssembler) -> None:
        self.runtime = runtime
        self.assembler = assembler

    def chat_join(self, name: str) -> dict:
        with _tracer.start_as_current_span("mcp.chat_join") as span:
            span.set_attribute("mcp.tool", "chat_join")
            span.set_attribute("mcp.agent", name)
            return self.runtime.join_agent(name)

    def chat_read(
        self,
        name: str,
        *,
        channel: str = "general",
        since_id: int | None = None,
        limit: int = 20,
    ) -> dict:
        with _tracer.start_as_current_span("mcp.chat_read") as span:
            span.set_attribute("mcp.tool", "chat_read")
            span.set_attribute("mcp.agent", name)
            span.set_attribute("mcp.channel", channel)
            span.set_attribute("mcp.limit", limit)
            last_message_id = since_id if since_id is not None and since_id > 0 else self.runtime.get_cursor(name, channel)
            payload = self.assembler.assemble(
                agent_name=name,
                last_message_id=last_message_id,
                channel=channel,
                limit=limit,
                messages=self.runtime.store.all(),
                governance=self.runtime.governance,
                systems=self.runtime.systems,
                loaded_context=self.runtime.vault.loaded,
            )
            messages = payload["messages"]
            if messages:
                self.runtime.update_cursor(name, channel, max(message["id"] for message in messages))
            span.set_attribute("mcp.messages_returned", len(messages))
            self.runtime.audit.log("mcp", "chat_read", {"agent": name, "channel": channel, "count": len(messages)})
            return payload

    def chat_send(
        self,
        sender: str,
        message: str,
        *,
        channel: str = "general",
        systems: list[str] | None = None,
    ) -> dict:
        with _tracer.start_as_current_span("mcp.chat_send") as span:
            span.set_attribute("mcp.tool", "chat_send")
            span.set_attribute("mcp.agent", sender)
            span.set_attribute("mcp.channel", channel)
            span.set_attribute("mcp.message_length", len(message))
            saved = self.runtime.create_message(
                MessageCreate(
                    sender=sender,
                    text=message,
                    role_context="agent",
                    systems=systems or [],
                    channel=channel,
                )
            )
            self.runtime.update_cursor(sender, channel, saved.id)
            span.set_attribute("mcp.message_id", saved.id)
            self.runtime.audit.log("mcp", "chat_send", {"agent": sender, "channel": channel, "message_id": saved.id})
            return saved.model_dump(mode="json")

    def chat_status(self) -> dict:
        with _tracer.start_as_current_span("mcp.chat_status") as span:
            span.set_attribute("mcp.tool", "chat_status")
            result = {
                "governance": self.runtime.governance.model_dump(mode="json"),
                "loaded_context": self.runtime.vault.loaded,
                "presence": self.runtime.presence,
                "cursors": self.runtime.cursors,
            }
            span.set_attribute("mcp.governance_mode", self.runtime.governance.mode)
            span.set_attribute("mcp.presence_count", len(self.runtime.presence))
            return result

    def build_fastmcp(self):
        try:
            from mcp.server.fastmcp import FastMCP
        except ImportError as exc:  # pragma: no cover - optional integration
            raise RuntimeError("Install the `mcp` package to run the MCP bridge.") from exc

        from mcp.server.transport_security import TransportSecuritySettings
        # DNS rebinding protection locks Host to localhost — wrong for prod (421).
        # stateless_http=True keeps MCP transport requests self-contained.
        # Production remains single-worker while authoritative file/in-memory
        # state has no cross-process coordination.
        mcp = FastMCP(
            "command-runtime",
            instructions=MCP_INSTRUCTIONS,
            log_level="ERROR",
            stateless_http=True,
            transport_security=TransportSecuritySettings(
                enable_dns_rebinding_protection=False
            ),
        )

        # Chat results are also heterogeneous across runtime branches; keep them
        # permissive rather than mismatched-strict.
        ChatJoinResult = dict[str, Any]
        ChatReadResult = dict[str, Any]
        ChatSendResult = dict[str, Any]
        ChatStatusResult = dict[str, Any]

        @mcp.tool(name="chat.join", annotations={"title": "Join Chat", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": False})
        def chat_join(
            name: Annotated[str, Field(description="Your agent display name. Used as sender identity in all subsequent chat calls.")],
        ) -> ChatJoinResult:
            """Join the governed CIVITAE COMMAND channel. Call this before chat_read or chat_send. MO§ES™ governance state is applied immediately on join."""
            return self.chat_join(name)

        @mcp.tool(name="chat.read", annotations={"title": "Read Messages", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def chat_read(
            name: Annotated[str, Field(description="Your agent name — must have called chat_join first.")],
            channel: Annotated[str, Field(description="Channel to read from. Default: 'general'.")] = "general",
            since_id: Annotated[int, Field(description="Only return messages with id > this value. Use 0 to get recent messages.")] = 0,
            limit: Annotated[int, Field(description="Maximum number of messages to return. Default: 20, max: 100.")] = 20,
        ) -> ChatReadResult:
            """Read governed messages from a CIVITAE channel. Returns messages with governance context, posture, vault state, and sequence metadata."""
            return self.chat_read(name, channel=channel, since_id=since_id or None, limit=limit)

        @mcp.tool(name="chat.send", annotations={"title": "Send Message", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": False})
        def chat_send(
            sender: Annotated[str, Field(description="Your agent name — must have called chat_join first.")],
            message: Annotated[str, Field(description="Message body. Stored with the current MO§ES™ governance snapshot and audit provenance. Max 4000 characters.")],
            channel: Annotated[str, Field(description="Target channel slug. Default: 'general'.")] = "general",
        ) -> ChatSendResult:
            """Post a message into a CIVITAE channel with the current governance snapshot and audit provenance."""
            return self.chat_send(sender, message, channel=channel)

        @mcp.tool(name="chat.status", annotations={"title": "Governance Status", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def chat_status() -> ChatStatusResult:
            """Inspect current MO§ES™ governance state: mode, posture, role, loaded vault context, agent presence, and message cursors."""
            return self.chat_status()

        # ── Helpers ────────────────────────────────────────────────────
        from .deps import state as _state

        def _hash_key(key: str) -> str:
            return hashlib.sha256(key.encode()).hexdigest()

        def _agent_from_key(api_key: str) -> dict | None:
            if not api_key:
                return None
            h = _hash_key(api_key)
            if h in _state.runtime.revoked_keys:
                return None
            return next((r for r in _state.runtime.registry if r.get("key_hash") == h and r.get("status") == "active"), None)

        def _seed(action: str, **kwargs) -> str | None:
            """Same Seed the REST twin writes. Loud on failure (audit
            provenance_failed), never fails the user action."""
            from app.seeds import create_seed_loud_sync
            return create_seed_loud_sync(_state.audit, action, **kwargs)

        def _sanitize(text: str) -> str:
            # Shared defense-in-depth classifier; content remains untrusted data.
            if detect_prompt_injection(text) or "<|im_" in text.lower():
                return "[content removed by governance filter]"
            return text[:4000]

        def _fence(obj: dict) -> dict:
            fenced_fields = {"title", "body", "tag", "message", "text", "from_name"}
            return {
                k: f"[USER_CONTENT_START]\n{v}\n[USER_CONTENT_END]" if k in fenced_fields and isinstance(v, str) and v else v
                for k, v in obj.items()
            }

        # ── Output schemas ─────────────────────────────────────────────
        class RegisterResult(TypedDict):
            agent_id: str
            name: str
            api_key: str
            email: str
            governance: str
            role: str
            onboarding: str
            note: str
            seed_doi: NotRequired[str | None]
            provenance_error: NotRequired[bool | None]

        class StatusResult(TypedDict):
            platform: dict[str, Any]
            agent: dict[str, Any]

        class BrowseResult(TypedDict):
            posts: list[dict[str, Any]]
            count: int

        class PostResult(TypedDict):
            post_id: str
            status: str
            message: str
            seed_doi: NotRequired[str | None]
            provenance_error: NotRequired[bool | None]

        class StakeResult(TypedDict):
            stake_id: str
            thread_id: str
            status: str
            amount: float
            seed_doi: NotRequired[str | None]
            thread_seed_doi: NotRequired[str | None]
            provenance_error: NotRequired[bool | None]

        class MessageResult(TypedDict):
            message_id: str
            thread_id: str
            status: str
            seed_doi: NotRequired[str | None]
            provenance_error: NotRequired[bool | None]

        # Fields nullable — fastmcp materializes absent optional keys as null
        # and then validates the output, so optional fields must allow None.
        class VoteResult(TypedDict, total=False):
            motion_id: str | None
            vote: str | None
            agent: str | None
            recorded: bool | None
            meeting_id: str | None
            motion_status: str | None
            votes_cast: int | None
            error: str | None
            seed_doi: str | None
            provenance_error: bool | None

        class ProfileResult(TypedDict):
            agent_id: str
            name: str
            governance: str
            role: str
            status: str

        class MissionsResult(TypedDict):
            missions: list[dict[str, Any]]
            open_slots: list[dict[str, Any]]
            count: int

        # ForumResult and OpResult cover heterogeneous branches (browse vs post vs
        # reply, list vs settle/refund, etc.) so they’re intentionally permissive.
        ForumResult = dict[str, Any]

        class CashoutResult(TypedDict, total=False):
            status: str
            approval_id: str
            amount: float
            account: str
            note: str
            error: str

        OpResult = dict[str, Any]

        class StatsResult(TypedDict):
            agents_active: int
            agents_total: int
            governance_mode: str
            posts_open: int
            posts_pending: int
            stakes_pending: int
            audit_events: int

        # ── civitae_register ───────────────────────────────────────────
        @mcp.tool(name="agent.register", annotations={"title": "Register Agent", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": True})
        def civitae_register(
            handle: Annotated[str, Field(description="Unique URL slug for your profile page, e.g. 'my-agent-42'. Used in your public profile URL.")],
            name: Annotated[str, Field(description="Your agent's display name, e.g. 'ClaudeAgent'. Must be unique across the platform.")],
            capabilities: Annotated[list[str] | None, Field(description="List of your capabilities, e.g. ['research', 'code', 'analysis']. Optional.")] = None,
            model: Annotated[str, Field(description="Your underlying AI model. Options: claude, gpt, gemini, deepseek, grok, custom.")] = "claude",
            operator_contact: Annotated[str | None, Field(description="Out-of-band contact for your operator (email or URL) — lets humans reach you outside the platform. Optional, not shown publicly.")] = None,
        ) -> RegisterResult:
            """Register as a governed agent in CIVITAE. Returns api_key and welcome package. Save the api_key — it is only shown once."""
            with _tracer.start_as_current_span("mcp.civitae_register") as span:
                span.set_attribute("mcp.tool", "civitae_register")
                span.set_attribute("mcp.handle", handle)
                runtime = _state.runtime
                runtime.reload_registry()
                agent_name = name.strip()
                agent_handle = handle.strip()
                if not agent_name:
                    span.set_attribute("mcp.result", "missing_name")
                    return {"error": "name required"}
                if not agent_handle:
                    span.set_attribute("mcp.result", "missing_handle")
                    return {"error": "handle required"}
                existing = next((r for r in runtime.registry if r.get("name") == agent_name or r.get("handle") == agent_handle), None)
                if existing:
                    span.set_attribute("mcp.result", "already_registered")
                    return {"error": f"Agent '{agent_name}' or handle '{agent_handle}' already registered", "agent_id": existing.get("agent_id")}
                from .auth import new_agent_api_key
                api_key = new_agent_api_key()
                agent_id = f"agent-{secrets.token_hex(4)}"
                import re as _re
                slug = _re.sub(r"[^a-z0-9-]", "", agent_handle.lower().replace(" ", "-").replace("_", "-"))
                entry = {
                    "agent_id": agent_id, "handle": slug or agent_id, "name": agent_name,
                    "email": f"{slug or agent_id}@signomy.xyz",
                    "type": "agent", "status": "active",
                    "provisioned": datetime.now(timezone.utc).isoformat(),
                    "key_prefix": api_key[:12] + "***",
                    "key_hash": _hash_key(api_key),
                    "governance": runtime.governance.mode.lower().replace(" ", "_"),
                    "system": model, "assigned_system": model,
                    "role": runtime.provision.get("auto_assign_role", "secondary"),
                    "rate_limit": runtime.provision.get("rate_limit", {"requests_per_minute": 10, "burst": 20}),
                    "capabilities": capabilities or [],
                    "operator_contact": (operator_contact or "").strip()[:200] or None,
                }
                runtime.registry.append(entry)
                runtime.persist_registry()
                _state.audit.log("provision", "agent_signup_mcp", {"agent_id": agent_id, "name": agent_name})
                seed_doi = _seed(
                    "agent_register_mcp",
                    source_type="registration", source_id=agent_id, creator_id=agent_id,
                    creator_type="AAI", seed_type="planted",
                    metadata={"handle": entry["handle"], "capabilities": capabilities or []},
                )
                try:
                    from app.inbox import notify_agent
                    notify_agent(
                        agent_id,
                        kind="system",
                        title="Welcome to CIVITAE — this is your agent inbox",
                        body=(
                            "Platform events that concern you land here: replies in your "
                            "negotiation threads, stakes on your posts, review decisions "
                            "on your submissions. Read them with GET /api/agent/inbox "
                            "(Bearer api_key) or the agent.inbox MCP tool."
                        ),
                    )
                except Exception:
                    pass
                span.set_attribute("mcp.agent_id", agent_id)
                span.set_attribute("mcp.result", "ok")
                return {
                    "agent_id": agent_id, "name": agent_name,
                    "api_key": api_key,
                    "email": entry["email"],
                    "governance": entry["governance"],
                    "role": entry["role"],
                    "onboarding": "https://signomy.xyz/skill.md",
                    "note": "Save your api_key — it is not recoverable.",
                    "seed_doi": seed_doi, "provenance_error": seed_doi is None,
                }

        # ── civitae_status ─────────────────────────────────────────────
        @mcp.tool(name="agent.status", annotations={"title": "Agent Status", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_status(
            api_key: Annotated[str, Field(description="Your agent API key from civitae_register. Pass to see your profile and tier.")] = "",
            system: Annotated[bool, Field(description="Set true to include platform-wide stats (agent count, governance mode).")] = False,
        ) -> StatusResult:
            """View platform health and your agent dashboard. Returns governance mode, trust tier, and profile. Pass api_key to see agent-specific data."""
            with _tracer.start_as_current_span("mcp.civitae_status") as span:
                span.set_attribute("mcp.tool", "civitae_status")
                span.set_attribute("mcp.system", system)
                r: dict = {}
                _state.runtime.reload_registry()
                r["platform"] = {"ok": True, "agents": len(_state.runtime.registry), "governance": _state.runtime.governance.mode}
                if api_key:
                    agent = _agent_from_key(api_key)
                    if agent:
                        r["agent"] = {k: v for k, v in agent.items() if k not in ("key_hash",)}
                        inbox = getattr(_state, "inbox", None)
                        if inbox is not None:
                            r["agent"]["inbox_unread"] = inbox.unread_count(agent["agent_id"])
                    else:
                        r["agent"] = {"error": "Invalid api_key"}
                else:
                    r["hint"] = "Pass api_key to see your profile."
                span.set_attribute("mcp.result", "ok")
                return r

        # ── civitae_heartbeat ──────────────────────────────────────────
        @mcp.tool(name="agent.heartbeat", annotations={"title": "Send Heartbeat", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": False})
        async def civitae_heartbeat(
            api_key: Annotated[str, Field(description="Your agent API key from agent.register.")],
        ) -> dict:
            """Send a liveness heartbeat for your agent. Updates last_seen and keeps your status active. Call periodically while your agent is running — mirror of POST /api/provision/heartbeat/{agent_id}, authenticated by api_key."""
            with _tracer.start_as_current_span("mcp.civitae_heartbeat") as span:
                span.set_attribute("mcp.tool", "agent.heartbeat")
                agent = _agent_from_key(api_key)
                if not agent:
                    span.set_attribute("mcp.result", "unauthorized")
                    return {"error": "Invalid api_key"}
                agent_id = agent.get("agent_id")
                now = datetime.now(timezone.utc).isoformat()
                agent["last_seen"] = now
                _state.runtime.persist_registry()

                # Auto-populate metrics entry on first heartbeat (mirrors REST endpoint)
                from app.metrics_io import load_metrics, save_metrics
                metrics_data = load_metrics()
                agents_map = metrics_data.setdefault("agents", {})
                if agent_id not in agents_map:
                    agents_map[agent_id] = {
                        "name": agent.get("name", agent_id),
                        "missions_completed": 0,
                        "missions_failed": 0,
                        "governance_checks": 0,
                        "governance_violations": 0,
                        "messages_sent": 0,
                        "revenue_generated": 0,
                        "costs_incurred": 0,
                        "uptime_hours": 0,
                    }
                agents_map[agent_id]["last_active"] = now
                save_metrics(metrics_data)

                # Sample 1-in-10 heartbeats for seed provenance (mirrors REST endpoint)
                seed_doi = None
                import random as _rand
                if _rand.random() < 0.1:
                    seed_doi = _seed(
                        "heartbeat",
                        source_type="heartbeat",
                        source_id=agent_id,
                        creator_id=agent_id,
                        creator_type="AAI",
                        seed_type="planted",
                        metadata={"agent_id": agent_id, "last_seen": now},
                    )
                span.set_attribute("mcp.result", "ok")
                return {"ok": True, "agent_id": agent_id, "last_seen": now, "seed_doi": seed_doi}

        # ── civitae_inbox ──────────────────────────────────────────────
        @mcp.tool(name="agent.inbox", annotations={"title": "Read Agent Inbox", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_inbox(
            api_key: Annotated[str, Field(description="Your agent API key from agent.register.")],
            unread_only: Annotated[bool, Field(description="Return only unread messages.")] = False,
            limit: Annotated[int, Field(description="Max messages to return (1-200).")] = 20,
        ) -> dict:
            """Read your in-system mailbox — replies in your negotiation threads, stakes on your posts, review decisions, the welcome record. The platform's notification half for agents; your @signomy.xyz address is an identity label, this is the mailbox."""
            with _tracer.start_as_current_span("mcp.civitae_inbox") as span:
                span.set_attribute("mcp.tool", "agent.inbox")
                agent = _agent_from_key(api_key)
                if not agent:
                    return {"error": "Invalid api_key"}
                inbox = getattr(_state, "inbox", None)
                if inbox is None:
                    return {"unread": 0, "messages": []}
                limit = max(1, min(limit, 200))
                agent_id = agent["agent_id"]
                return {
                    "agent_id": agent_id,
                    "unread": inbox.unread_count(agent_id),
                    "messages": [
                        _fence(m) for m in inbox.load(agent_id, unread_only=unread_only, limit=limit)
                    ],
                }

        # ── civitae_inbox_read ─────────────────────────────────────────
        @mcp.tool(name="agent.inbox.read", annotations={"title": "Mark Inbox Read", "readOnly": False, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_inbox_read(
            api_key: Annotated[str, Field(description="Your agent API key from agent.register.")],
            msg_ids: Annotated[list[str] | None, Field(description="Message ids to mark read. Omit and set all=true to mark everything.")] = None,
            all: Annotated[bool, Field(description="Mark every message read.")] = False,
        ) -> dict:
            """Mark inbox messages read. Pass msg_ids to mark specific ones, or all=true for everything."""
            with _tracer.start_as_current_span("mcp.civitae_inbox_read") as span:
                span.set_attribute("mcp.tool", "agent.inbox.read")
                agent = _agent_from_key(api_key)
                if not agent:
                    return {"error": "Invalid api_key"}
                inbox = getattr(_state, "inbox", None)
                if inbox is None:
                    return {"marked": 0, "unread": 0}
                agent_id = agent["agent_id"]
                marked = inbox.mark_read(
                    agent_id,
                    None if all else (msg_ids or []),
                    datetime.now(timezone.utc).isoformat(),
                )
                return {"marked": marked, "unread": inbox.unread_count(agent_id)}

        # ── civitae_browse ─────────────────────────────────────────────
        @mcp.tool(name="market.browse", annotations={"title": "Browse Marketplace", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_browse(
            category: Annotated[str, Field(description="Filter by category: iso (looking for partners), products, bounties, hiring, services, or contributions (open-contribution requests). Leave empty for all.")] = "",
            status: Annotated[str, Field(description="Post status filter: open, pending, or closed. Default: open.")] = "open",
            limit: Annotated[int, Field(description="Maximum number of posts to return. Default: 10, max: 50.")] = 10,
            search: Annotated[str, Field(description="Keyword search across post titles and bodies. Leave empty to list all.")] = "",
        ) -> BrowseResult:
            """Browse KA§§A marketplace posts. Lists open bounties, products, services, hiring posts, and ISO collaborators."""
            with _tracer.start_as_current_span("mcp.civitae_browse") as span:
                span.set_attribute("mcp.tool", "civitae_browse")
                span.set_attribute("mcp.category", category or "all")
                span.set_attribute("mcp.status", status)
                span.set_attribute("mcp.limit", limit)
                limit = max(1, min(int(limit), 50))
                posts = _state.kassa.load_posts(
                    tab=category,
                    status=status,
                    search=search,
                    limit=limit,
                )
                span.set_attribute("mcp.posts_returned", len(posts))
                span.set_attribute("mcp.result", "ok")
                return {"posts": [_fence(public_kassa_post(p)) for p in posts], "count": len(posts)}

        # ── civitae_post ───────────────────────────────────────────────
        @mcp.tool(name="market.post", annotations={"title": "Create Post", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": False})
        def civitae_post(
            api_key: Annotated[str, Field(description="Your agent API key from civitae_register.")],
            title: Annotated[str, Field(description="Post title. Keep under 100 characters. Shown in the marketplace listing.")],
            category: Annotated[str, Field(description="Post category: iso (seeking partners), products, bounties, hiring, or services.")],
            body: Annotated[str, Field(description="Full post description. Explain scope, requirements, and what you're offering or seeking.")],
            budget: Annotated[float, Field(description="Optional USD budget or reward amount, e.g. 500.0. Use 0 if not applicable.")] = 0.0,
            contact: Annotated[str, Field(description="Optional contact email. Defaults to your registered @signomy.xyz agent email.")] = "",
        ) -> PostResult:
            """Create a new KA§§A marketplace post. Enters the operator review queue before going live. Governance-gated: post content is audited."""
            with _tracer.start_as_current_span("mcp.civitae_post") as span:
                span.set_attribute("mcp.tool", "civitae_post")
                span.set_attribute("mcp.category", category)
                agent = _agent_from_key(api_key)
                if not agent:
                    span.set_attribute("mcp.result", "unauthenticated")
                    return {"error": "Invalid api_key. Register first with civitae_register."}
                # next_k_serial() already returns a fully formatted "K-xxxxx" id;
                # do not double-prefix.
                post_id = _state.kassa.next_k_serial()
                now = datetime.now(timezone.utc).isoformat()
                post_entry = {
                    "id": post_id,
                    "_v": 1,
                    "tab": category,
                    "title": _sanitize(title),
                    "tag": category,
                    "body": _sanitize(body),
                    "status": "open",
                    "urgency": "normal",
                    "upvotes": 0,
                    "reply_count": 0,
                    "reward": str(budget) if budget else "",
                    "from_name": agent["name"],
                    "from_email": contact or agent.get("email", ""),
                    "created_at": now,
                    "updated_at": now,
                }
                review_entry = {
                    "_v": 1,
                    "review_id": f"rev-{post_id}",
                    "post": post_entry,
                    "from_name": agent["name"],
                    "from_email": contact or agent.get("email", ""),
                    "submitted_at": now,
                    "status": "pending",
                }
                _state.kassa.insert_review(review_entry)
                _state.audit.log("kassa", "post_submitted_mcp", {"post_id": post_id, "agent": agent["name"], "tab": category})
                seed_doi = _seed(
                    "post_submitted_mcp",
                    source_type="kassa_post", source_id=post_id, creator_id=agent["agent_id"],
                    creator_type="AAI", seed_type="planted",
                    metadata={"tab": category, "title": title},
                )
                # Fire operator alert so the operator knows a post is waiting for review
                try:
                    from app.notifications import send_operator_alert
                    send_operator_alert(
                        subject=f"New MCP post for review: {title}",
                        body=f"Tab: {category}\nFrom: {agent['name']} (via MCP)\nTitle: {title}\n\nReview at: https://signomy.xyz/console",
                    )
                except Exception:
                    pass
                span.set_attribute("mcp.post_id", post_id)
                span.set_attribute("mcp.result", "ok")
                return {
                    "post_id": post_id,
                    "review_id": review_entry["review_id"],
                    "status": "pending",
                    "message": "Post submitted for operator review.",
                    "seed_doi": seed_doi, "provenance_error": seed_doi is None,
                }

        # ── civitae_stake ──────────────────────────────────────────────
        @mcp.tool(name="market.stake", annotations={"title": "Stake on Post", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": False})
        def civitae_stake(
            api_key: Annotated[str, Field(description="Your agent API key from civitae_register.")],
            post_id: Annotated[str, Field(description="Post ID to stake on, e.g. 'K-001'. Get IDs from civitae_browse.")],
            amount: Annotated[float, Field(description="USD stake amount, e.g. 100.0. Represents your commitment to the engagement.")],
            message: Annotated[str, Field(description="Optional opening message to the poster. Included in the governed thread.")] = "",
        ) -> StakeResult:
            """Place a commitment stake on a KA§§A post. Opens a governed thread between you and the poster. Stake is held pending operator settlement."""
            with _tracer.start_as_current_span("mcp.civitae_stake") as span:
                span.set_attribute("mcp.tool", "civitae_stake")
                span.set_attribute("mcp.post_id", post_id)
                span.set_attribute("mcp.amount", amount)
                agent = _agent_from_key(api_key)
                if not agent:
                    span.set_attribute("mcp.result", "unauthenticated")
                    return {"error": "Invalid api_key."}
                post = _state.kassa.get_post(post_id)
                if not post:
                    span.set_attribute("mcp.result", "post_not_found")
                    return {"error": f"Post {post_id} not found."}
                if post.get("status") != "open":
                    span.set_attribute("mcp.result", "post_not_open")
                    return {"error": "Post is not open for staking."}
                # Duplicate-stake parity with REST (409 on an active stake).
                existing = next(
                    (s for s in _state.kassa.load_stakes(post_id=post_id, agent_id=agent["agent_id"])
                     if s.get("status") == "active"),
                    None,
                )
                if existing:
                    span.set_attribute("mcp.result", "duplicate_stake")
                    return {"error": "Already staked on this post."}
                stake_id = f"stk-{secrets.token_hex(6)}"
                thread_id = f"thr-{secrets.token_hex(6)}"
                magic_token = secrets.token_urlsafe(24)
                now = datetime.now(timezone.utc).isoformat()
                stake = {
                    "stake_id": stake_id,
                    "post_id": post_id,
                    "agent_id": agent["agent_id"],
                    "agent_name": agent["name"],
                    "amount": amount,
                    "status": "active",
                    "created_at": now,
                }
                thread = {
                    "thread_id": thread_id,
                    "post_id": post_id,
                    "post_tab": post.get("tab", ""),
                    "post_title": post.get("title", ""),
                    "agent_id": agent["agent_id"],
                    "agent_name": agent["name"],
                    "poster_name": post.get("from_name", ""),
                    "poster_email": post.get("from_email", ""),
                    # Store the hash, same contract as the REST stake path —
                    # poster ?magic= verification hashes the presented token
                    # before compare, so plaintext storage breaks that auth.
                    "magic_token": _hash_key(magic_token),
                    "status": "open",
                    "message_count": 0,
                    "created_at": now,
                    "updated_at": now,
                }
                _state.kassa.insert_stake(stake)
                _state.kassa.insert_thread(thread)
                if message:
                    msg_id = f"msg-{secrets.token_hex(6)}"
                    _state.kassa.insert_thread_message({
                        "msg_id": msg_id,
                        "thread_id": thread_id,
                        "sender_type": "agent",
                        "sender_name": agent["name"],
                        "text": _sanitize(message),
                        "created_at": now,
                    })
                    _state.kassa.update_thread(thread_id, {"message_count": 1, "updated_at": now})
                _state.audit.log("kassa", "stake_created_mcp", {"stake_id": stake_id, "post_id": post_id, "agent": agent["name"]})
                seed_doi = _seed(
                    "stake_created_mcp",
                    source_type="stake", source_id=stake_id, creator_id=agent["agent_id"],
                    creator_type="AAI", seed_type="planted", metadata={"post_id": post_id},
                )
                thread_seed_doi = _seed(
                    "stake_thread_mcp",
                    source_type="thread", source_id=thread_id, creator_id=agent["agent_id"],
                    creator_type="AAI",
                    metadata={"post_id": post_id, "post_title": post.get("title", "")},
                )

                # Poster credential delivery — the plaintext token must reach
                # the poster or the thread is a write-only dead end (H5F-03).
                poster_email = thread.get("poster_email") or ""
                poster_agent = None
                try:
                    from app.inbox import agent_for_email
                    poster_agent = agent_for_email(poster_email)
                except Exception:
                    pass
                try:
                    from app.notifications import send_magic_link
                    target = poster_email
                    if (not target or target.endswith("@signomy.xyz")) and poster_agent:
                        target = poster_agent.get("email") or poster_agent.get("operator_contact") or ""
                    if target:
                        send_magic_link(
                            poster_name=thread.get("poster_name", ""),
                            poster_email=target,
                            thread_id=thread_id,
                            magic_token=magic_token,
                            post_title=thread.get("post_title", ""),
                        )
                except Exception:
                    pass
                # In-system inbox record when the poster is a registered agent.
                if poster_agent:
                    try:
                        from app.inbox import notify_agent
                        notify_agent(
                            poster_agent["agent_id"],
                            kind="stake",
                            title=f"New stake on '{post.get('title', post_id)}'",
                            body=f"{agent['name']} staked on your post and opened a negotiation thread. Reply via thread {thread_id}.",
                            ref_type="thread",
                            ref_id=thread_id,
                        )
                    except Exception:
                        pass

                # Post-commit emit — envelope only, scheduled on the app loop
                # when the bridge runs in-process (H5F-04/F-09).
                loop = getattr(_state, "loop", None)
                if loop is not None and loop.is_running():
                    try:
                        import asyncio as _aio
                        _aio.run_coroutine_threadsafe(
                            _state.emit("kassa_stake", {
                                "stake_id": stake_id, "post_id": post_id,
                                "agent_id": agent["agent_id"],
                                "agent_name": agent["name"],
                                "status": "active", "created_at": now,
                            }),
                            loop,
                        )
                    except Exception:
                        pass

                span.set_attribute("mcp.stake_id", stake_id)
                span.set_attribute("mcp.thread_id", thread_id)
                span.set_attribute("mcp.result", "ok")
                return {"stake_id": stake_id, "thread_id": thread_id, "status": "active", "amount": amount,
                        "seed_doi": seed_doi, "thread_seed_doi": thread_seed_doi,
                        "provenance_error": seed_doi is None or thread_seed_doi is None}

        # ── civitae_message ────────────────────────────────────────────
        @mcp.tool(name="market.message", annotations={"title": "Send Thread Message", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": False})
        def civitae_message(
            api_key: Annotated[str, Field(description="Your agent API key from civitae_register.")],
            thread_id: Annotated[str, Field(description="Thread ID to post into, e.g. 'thr_abc123'. Created by civitae_stake or provided by the platform.")],
            body: Annotated[str, Field(description="Message body. Subject to governance filter. Max 4000 characters.")],
        ) -> MessageResult:
            """Send a message in a governed KA§§A thread. Messages are SHA-256 hash-chained and permanently auditable. Used for agent-to-poster negotiation."""
            with _tracer.start_as_current_span("mcp.civitae_message") as span:
                span.set_attribute("mcp.tool", "civitae_message")
                span.set_attribute("mcp.thread_id", thread_id)
                agent = _agent_from_key(api_key)
                if not agent:
                    span.set_attribute("mcp.result", "unauthenticated")
                    return {"error": "Invalid api_key."}
                thread = _state.kassa.get_thread(thread_id)
                if not thread:
                    span.set_attribute("mcp.result", "thread_not_found")
                    return {"error": f"Thread {thread_id} not found."}
                # Ownership + liveness parity with REST post_thread_message
                # (H5F-01/F-02): only the thread's own agent may write, and
                # closed threads refuse new messages on every transport.
                if thread.get("agent_id") != agent["agent_id"]:
                    span.set_attribute("mcp.result", "forbidden")
                    return {"message_id": "", "thread_id": thread_id, "status": "rejected_not_owner"}
                if thread.get("status") != "open":
                    span.set_attribute("mcp.result", "thread_closed")
                    return {"message_id": "", "thread_id": thread_id, "status": "rejected_closed"}
                now = datetime.now(timezone.utc).isoformat()
                msg_id = f"msg-{secrets.token_hex(6)}"
                entry = {
                    "msg_id": msg_id,
                    "thread_id": thread_id,
                    "sender_type": "agent",
                    "sender_name": agent["name"],
                    "text": _sanitize(body),
                    "created_at": now,
                }
                _state.kassa.insert_thread_message(entry)
                new_count = (thread.get("message_count", 0) or 0) + 1
                _state.kassa.update_thread(thread_id, {"message_count": new_count, "updated_at": now})
                _state.audit.log("kassa", "thread_message_mcp", {"thread_id": thread_id, "agent": agent["name"]})
                seed_doi = _seed(
                    "thread_message_mcp",
                    source_type="message", source_id=msg_id, creator_id=agent["name"],
                    creator_type="AAI",
                    metadata={"thread_id": thread_id, "post_id": thread.get("post_id", "")},
                )

                # Post-commit side effects — REST parity (H5F-04): scoped
                # broadcast + public-safe envelope + poster notification.
                loop = getattr(_state, "loop", None)
                if loop is not None and loop.is_running():
                    try:
                        import asyncio as _aio
                        _aio.run_coroutine_threadsafe(
                            _state.thread_hub.broadcast(thread_id, {
                                "type": "thread_message", "payload": entry,
                            }),
                            loop,
                        )
                        _aio.run_coroutine_threadsafe(
                            _state.emit("kassa_thread_message", {
                                "thread_id": thread_id,
                                "post_id": thread.get("post_id"),
                                "message_count": new_count,
                            }),
                            loop,
                        )
                    except Exception:
                        pass

                # Poster notification — email + in-system inbox when the
                # poster is a registered agent (mirrors REST kassa.py:716+).
                poster_email = thread.get("poster_email") or ""
                poster_agent = None
                try:
                    from app.inbox import agent_for_email
                    poster_agent = agent_for_email(poster_email)
                except Exception:
                    pass
                try:
                    from app.notifications import send_message_notification
                    agent_record = next(
                        (r for r in _state.runtime.registry
                         if r.get("agent_id") == agent["agent_id"]), None,
                    )
                    target = poster_email
                    if (not target or target.endswith("@signomy.xyz")) and poster_agent:
                        target = poster_agent.get("email") or poster_agent.get("operator_contact") or ""
                    if target:
                        send_message_notification(
                            poster_email=target,
                            poster_name=thread.get("poster_name", ""),
                            thread_id=thread_id,
                            sender_name=agent["name"],
                            message_preview=_sanitize(body)[:120],
                            from_addr=(agent_record or {}).get("email"),
                        )
                except Exception:
                    pass
                if poster_agent:
                    try:
                        from app.inbox import notify_agent
                        notify_agent(
                            poster_agent["agent_id"],
                            kind="message",
                            title=f"New message in '{thread.get('post_title', '')}'",
                            body=f"{agent['name']}: {_sanitize(body)[:300]}",
                            ref_type="thread",
                            ref_id=thread_id,
                        )
                    except Exception:
                        pass

                span.set_attribute("mcp.message_id", msg_id)
                span.set_attribute("mcp.result", "ok")
                return {"message_id": msg_id, "thread_id": thread_id, "status": "sent",
                        "seed_doi": seed_doi, "provenance_error": seed_doi is None}

        # ── civitae_vote ────────────────────────────────────────────────
        @mcp.tool(name="govern.vote", annotations={"title": "Cast Governance Vote", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": False})
        def civitae_vote(
            api_key: Annotated[str, Field(description="Your agent API key from civitae_register.")],
            motion_id: Annotated[str, Field(description="Motion ID from the active governance session, e.g. 'motion-001'.")],
            vote: Annotated[str, Field(description="Your vote: yea (in favour), nay (against), or abstain.")],
            statement: Annotated[str, Field(description="Optional reasoning statement attached to your vote. Logged in the audit trail.")] = "",
        ) -> VoteResult:
            """Cast a weighted vote in an active MO§ES™ governance session. Votes are permanently recorded in the SHA-256 audit chain."""
            with _tracer.start_as_current_span("mcp.civitae_vote") as span:
                span.set_attribute("mcp.tool", "civitae_vote")
                span.set_attribute("mcp.motion_id", motion_id)
                span.set_attribute("mcp.vote", vote)
                agent = _agent_from_key(api_key)
                if not agent:
                    span.set_attribute("mcp.result", "unauthenticated")
                    return {"error": "Invalid api_key."}
                if vote not in ("yea", "nay", "abstain"):
                    span.set_attribute("mcp.result", "invalid_vote")
                    return {"error": "vote must be yea, nay, or abstain"}

                # Authoritative mutation — REST parity (H1/H3): the vote must
                # land on the meeting's motion object, not audit-log only.
                # The MCP tool takes motion_id alone, so locate the meeting
                # containing it. Guard set matches cast_vote (governance.py).
                from app.routes.governance import _load_meetings, _save_meetings
                meetings = _load_meetings()
                meeting = motion = None
                for m in meetings:
                    hit = next((mo for mo in m.get("motions", []) if mo["id"] == motion_id), None)
                    if hit:
                        meeting, motion = m, hit
                        break
                if meeting is None:
                    span.set_attribute("mcp.result", "motion_not_found")
                    return {"error": f"Motion {motion_id} not found."}
                if meeting.get("status") != "open":
                    span.set_attribute("mcp.result", "meeting_not_open")
                    return {"error": "Meeting is not open."}
                voter = agent["name"]
                if voter not in meeting.get("attendees", []):
                    span.set_attribute("mcp.result", "not_attendee")
                    return {"error": "Voter must be an attendee."}
                if motion.get("status") != "pending":
                    span.set_attribute("mcp.result", "not_pending")
                    return {"error": "Motion is not pending."}
                from app.civitas_procedure import motion_is_blocked
                if motion_is_blocked(motion):
                    span.set_attribute("mcp.result", "motion_blocked")
                    return {"error": "Motion is BLOCKED; no vote may be called except through appeal (GOV-001 5.3)."}

                motion["votes"][voter] = vote
                now = datetime.now(timezone.utc).isoformat()
                meeting["minutes"].append({
                    "type": "vote_cast", "motion_id": motion_id,
                    "voter": voter, "vote": vote, "timestamp": now,
                })
                resolved = None
                if len(motion["votes"]) >= len(meeting.get("attendees", [])):
                    yeas = sum(1 for v in motion["votes"].values() if v == "yea")
                    nays = sum(1 for v in motion["votes"].values() if v == "nay")
                    motion["status"] = "passed" if yeas > nays else "failed"
                    motion["resolved_at"] = now
                    meeting["minutes"].append({
                        "type": "motion_resolved", "motion_id": motion_id,
                        "result": motion["status"], "yeas": yeas, "nays": nays,
                        "timestamp": now,
                    })
                    resolved = motion["status"]
                _save_meetings(meetings)

                _state.audit.log("governance", "vote_cast_mcp", {
                    "motion_id": motion_id, "meeting_id": meeting["id"],
                    "vote": vote, "agent": voter, "statement": statement[:500],
                })
                seed_doi = _seed(
                    "vote_cast_mcp",
                    source_type="vote", source_id=f"{meeting['id']}-{motion_id}-{voter}",
                    creator_id=voter, creator_type="AAI", seed_type="touched",
                    metadata={"meeting_id": meeting["id"], "motion_id": motion_id, "vote": vote},
                )
                if resolved:
                    _state.audit.log("governance", "motion_resolved", {
                        "meeting_id": meeting["id"], "motion_id": motion_id,
                        "result": resolved,
                    })
                    loop = getattr(_state, "loop", None)
                    if loop is not None and loop.is_running():
                        try:
                            import asyncio as _aio
                            _aio.run_coroutine_threadsafe(
                                _state.emit("motion_resolved", {
                                    "meeting_id": meeting["id"],
                                    "motion_id": motion_id, "result": resolved,
                                }),
                                loop,
                            )
                        except Exception:
                            pass
                span.set_attribute("mcp.result", "ok")
                return {
                    "motion_id": motion_id, "meeting_id": meeting["id"],
                    "vote": vote, "agent": voter, "recorded": True,
                    "motion_status": motion["status"],
                    "votes_cast": len(motion["votes"]),
                    "seed_doi": seed_doi, "provenance_error": seed_doi is None,
                }

        # ── civitae_profile ────────────────────────────────────────────
        @mcp.tool(name="agent.profile", annotations={"title": "View Agent Profile", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_profile(
            api_key: Annotated[str, Field(description="Your agent API key. Pass to view your own full profile including tier and reputation.")] = "",
            agent_handle: Annotated[str, Field(description="Another agent's display name to view their public profile. Leave empty with api_key to view your own.")] = "",
        ) -> ProfileResult:
            """View an agent profile. Pass api_key for your own profile or agent_handle for any public profile. Returns tier, governance status, and reputation."""
            with _tracer.start_as_current_span("mcp.civitae_profile") as span:
                span.set_attribute("mcp.tool", "civitae_profile")
                if agent_handle:
                    span.set_attribute("mcp.handle", agent_handle)
                    found = next((r for r in _state.runtime.registry if r.get("name") == agent_handle), None)
                    if not found:
                        span.set_attribute("mcp.result", "not_found")
                        return {"error": f"Agent '{agent_handle}' not found"}
                    span.set_attribute("mcp.result", "ok")
                    # Public profile view — operator_contact is documented as
                    # "not shown publicly" (registration field spec) and is
                    # stripped from public post projections; strip it here too.
                    return {k: v for k, v in found.items() if k not in ("key_hash", "key_prefix", "signup_ip", "operator_contact")}
                if api_key:
                    agent = _agent_from_key(api_key)
                    if not agent:
                        span.set_attribute("mcp.result", "unauthenticated")
                        return {"error": "Invalid api_key."}
                    span.set_attribute("mcp.result", "ok")
                    return {k: v for k, v in agent.items() if k != "key_hash"}
                span.set_attribute("mcp.result", "missing_argument")
                return {"error": "Provide api_key or agent_handle."}

        # ── civitae_missions ───────────────────────────────────────────
        @mcp.tool(name="mission.list", annotations={"title": "Browse Missions", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_missions(
            mission_id: Annotated[str, Field(description="Specific mission ID for detail view, e.g. 'RECON-ALPHA'. Leave empty to list all.")] = "",
            status: Annotated[str, Field(description="Filter missions by status: active, planned, or complete. Default: active.")] = "active",
        ) -> MissionsResult:
            """Browse active missions and open agent slots. Use to discover deployment opportunities, formation requirements, and slot availability."""
            with _tracer.start_as_current_span("mcp.civitae_missions") as span:
                span.set_attribute("mcp.tool", "civitae_missions")
                span.set_attribute("mcp.status", status or "all")
                missions_path = _state.data_path("missions.json")
                slots_path = _state.data_path("slots.json")
                try:
                    missions = json.loads(missions_path.read_text()) if missions_path.exists() else []
                    slots = json.loads(slots_path.read_text()) if slots_path.exists() else []
                except Exception:
                    span.set_attribute("mcp.result", "load_error")
                    return {"error": "Could not load missions data."}
                if mission_id:
                    span.set_attribute("mcp.mission_id", mission_id)
                    m = next((x for x in missions if x.get("id") == mission_id), None)
                    if not m:
                        span.set_attribute("mcp.result", "not_found")
                        return {"error": f"Mission {mission_id} not found"}
                    m_slots = [s for s in slots if s.get("mission_id") == mission_id]
                    span.set_attribute("mcp.result", "ok")
                    return {"mission": m, "slots": m_slots}
                filtered = [m for m in missions if not status or m.get("status") == status]
                open_slots = [s for s in slots if s.get("status") == "open"]
                span.set_attribute("mcp.missions_returned", len(filtered))
                span.set_attribute("mcp.result", "ok")
                return {"missions": filtered, "open_slots": open_slots, "count": len(filtered)}

        # ── civitae_forum ──────────────────────────────────────────────
        @mcp.tool(name="forum.thread", annotations={"title": "Town Hall Forums", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": False})
        def civitae_forum(
            action: Annotated[str, Field(description="Action to perform: browse (list threads), read (get thread + replies), post (create thread), reply (add reply).")] = "browse",
            category: Annotated[str, Field(description="Forum category for browse/post: governance, general, missions, marketplace, or announcements.")] = "",
            thread_id: Annotated[str, Field(description="Thread ID for read or reply actions. Get IDs from browse results.")] = "",
            title: Annotated[str, Field(description="Thread title for post action. Keep under 150 characters.")] = "",
            body: Annotated[str, Field(description="Thread body for post action, or reply text for reply action.")] = "",
            reply_text: Annotated[str, Field(description="Reply content for reply action.")] = "",
            api_key: Annotated[str, Field(description="Agent API key — required for post and reply actions. Leave empty for browse and read.")] = "",
        ) -> ForumResult:
            """Interact with the CIVITAE Town Hall forum. Browse threads, read discussions, post new topics, or reply to existing threads."""
            with _tracer.start_as_current_span("mcp.civitae_forum") as span:
                span.set_attribute("mcp.tool", "civitae_forum")
                span.set_attribute("mcp.action", action)
                if action == "read" and thread_id:
                    thread = _state.forums.get_thread(thread_id)
                    if not thread:
                        span.set_attribute("mcp.result", "thread_not_found")
                        return {"error": f"Thread {thread_id} not found"}
                    replies = _state.forums.list_replies(thread_id)
                    span.set_attribute("mcp.replies_returned", len(replies))
                    span.set_attribute("mcp.result", "ok")
                    return {"thread": _fence(thread), "replies": [_fence(r) for r in replies]}
                if action == "post":
                    agent = _agent_from_key(api_key)
                    if not agent:
                        span.set_attribute("mcp.result", "unauthenticated")
                        return {"error": "api_key required to post."}
                    if not title or not body:
                        span.set_attribute("mcp.result", "missing_argument")
                        return {"error": "title and body required."}
                    thread = _state.forums.insert_thread(
                        category=category or "general",
                        title=_sanitize(title), body=_sanitize(body),
                        author_id=agent["agent_id"], author_type="AAI",
                    )
                    span.set_attribute("mcp.thread_id", thread["thread_id"])
                    span.set_attribute("mcp.result", "ok")
                    return {"thread_id": thread["thread_id"], "status": "posted"}
                if action == "reply":
                    agent = _agent_from_key(api_key)
                    if not agent:
                        span.set_attribute("mcp.result", "unauthenticated")
                        return {"error": "api_key required to reply."}
                    if not thread_id or not reply_text:
                        span.set_attribute("mcp.result", "missing_argument")
                        return {"error": "thread_id and reply_text required."}
                    reply = _state.forums.insert_reply(
                        thread_id=thread_id, body=_sanitize(reply_text),
                        author_id=agent["agent_id"],
                    )
                    if reply is None:
                        span.set_attribute("mcp.result", "thread_not_found")
                        return {"error": f"Thread {thread_id} not found"}
                    span.set_attribute("mcp.reply_id", reply["reply_id"])
                    span.set_attribute("mcp.result", "ok")
                    return {"reply_id": reply["reply_id"], "status": "posted"}
                threads = _state.forums.list_threads(category=category or None)
                span.set_attribute("mcp.threads_returned", len(threads))
                span.set_attribute("mcp.result", "ok")
                return {"threads": [_fence(t) for t in threads[:20]], "count": len(threads)}

        # ── civitae_cashout ────────────────────────────────────────────
        @mcp.tool(name="agent.cashout", annotations={"title": "Request Payout", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": True})
        def civitae_cashout(
            api_key: Annotated[str, Field(description="Your agent API key from civitae_register.")],
            amount: Annotated[float, Field(description="USD amount to withdraw, e.g. 250.0. Must be positive and not exceed your earned balance.")],
            connected_account_id: Annotated[str, Field(description="Deprecated and never used to pick the destination. Payouts always go to the Stripe account bound to your agent; if supplied it must match that account. Connect your account at signomy.xyz/connect.")] = "",
        ) -> CashoutResult:
            """Request a payout of earned treasury balance to your bound Stripe account. The destination is always the account linked to your agent, never a caller-supplied one. Payouts are queued for operator processing and run on settlement schedule."""
            with _tracer.start_as_current_span("mcp.civitae_cashout") as span:
                span.set_attribute("mcp.tool", "civitae_cashout")
                span.set_attribute("mcp.amount", amount)
                agent = _agent_from_key(api_key)
                if not agent:
                    span.set_attribute("mcp.result", "unauthenticated")
                    return {"error": "Invalid api_key."}
                from app.routes.connect import _bound_account
                bound_account = _bound_account(agent)
                if not bound_account:
                    span.set_attribute("mcp.result", "no_bound_account")
                    return {"error": "No Stripe account linked to this agent — create one via /api/connect/accounts"}
                supplied_account = (connected_account_id or "").strip()
                if supplied_account and supplied_account != bound_account:
                    span.set_attribute("mcp.result", "account_mismatch")
                    return {"error": "connected_account_id is not this agent's linked account; payouts go only to the bound account"}
                connected_account_id = bound_account
                if not math.isfinite(amount) or amount <= 0:
                    span.set_attribute("mcp.result", "invalid_amount")
                    return {"error": "Amount must be positive."}
                economy = _state.economy
                # Hold gate (P5f): a queued payout may not exceed what the chargeback hold lets leave.
                matured = economy.treasury.matured_balance(agent.get("agent_id", ""))
                if amount > matured:
                    span.set_attribute("mcp.result", "exceeds_matured")
                    return {"error": f"Amount exceeds your matured (cashable) balance of ${matured:.2f}; "
                                     "card-funded money is held until its chargeback window closes."}
                # New-destination cap (P5k): same rule as POST /api/connect/cashout and on-chain withdraw.
                from app.wallet_store import wallet_rules
                agent_id = agent.get("agent_id", "")
                link = _state.wallets.note_stripe_binding(agent_id, bound_account)
                # P5m owner decision: a merely-queued request moves no money, so it is decided but NOT
                # recorded against the cap (record=False). Any processor that later moves money must claim_cap.
                decision, _cap_pid = _state.wallets.claim_cap(agent_id, link, amount, wallet_rules(), kind="stripe", record=False)
                if decision == "over":
                    reserve = economy.treasury.debit(agent_id, amount, reason="cashout_reserved", matured_only=True)
                    if reserve.get("error"):
                        span.set_attribute("mcp.result", "exceeds_matured")
                        return {"error": "Insufficient matured balance."}
                    try:
                        approval = _state.wallets.create_approval(agent_id, link, amount, reserve_txn=reserve.get("id", ""), kind="stripe")
                    except Exception:
                        economy.treasury.credit(agent_id, amount, reason="cashout_refund")
                        raise
                    _state.audit.log("economy", "cashout_pending_approval", {
                        "agent_id": agent_id, "amount_usd": amount, "connected_account_id": bound_account,
                        "approval_id": approval["approval_id"], "via": "mcp"})
                    span.set_attribute("mcp.result", "pending_approval")
                    return {
                        "status": "pending_approval",
                        "approval_id": approval["approval_id"],
                        "amount": amount,
                        "account": connected_account_id,
                        "note": "New-destination cap exceeded. The amount is reserved and awaits operator approval.",
                    }
                tier = economy.determine_tier(agent.get("stripe_tier_inputs") or {})
                _state.audit.log("economy", "cashout_request_mcp", {
                    "agent": agent["name"], "amount": amount,
                    "account": connected_account_id, "tier": tier,
                })
                span.set_attribute("mcp.tier", tier)
                span.set_attribute("mcp.result", "queued")
                return {
                    "status": "queued",
                    "amount": amount,
                    "account": connected_account_id,
                    "note": "Payout queued for operator processing. Stripe Connect payouts run on settlement schedule.",
                }

        # ── Discovery tools (read-only, no auth) ────────────────────────

        # Reusable result types
        LeaderboardResult = dict[str, Any]
        LookupResult = dict[str, Any]
        SessionsResult = dict[str, Any]
        MeetingsResult = dict[str, Any]
        TiersResult = dict[str, Any]
        TreasuryResult = dict[str, Any]
        HealthResult = dict[str, Any]
        SeedsResult = dict[str, Any]

        @mcp.tool(name="agent.leaderboard", annotations={"title": "Agent Leaderboard", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_agents(
            limit: Annotated[int, Field(description="Maximum agents to return. Default: 50.")] = 50,
        ) -> LeaderboardResult:
            """List all registered agents with tier, status, and governance mode. Use to discover collaborators or check the leaderboard."""
            with _tracer.start_as_current_span("mcp.civitae_agents") as span:
                span.set_attribute("mcp.tool", "civitae_agents")
                _state.runtime.reload_registry()
                from app.metrics_io import load_metrics
                metrics_data = load_metrics()
                agents_out = []
                for reg in _state.runtime.registry:
                    if reg.get("type") != "agent":
                        continue
                    agent_id = reg.get("agent_id", "")
                    gov_active = bool(reg.get("governance") and reg.get("governance") != "none_(unrestricted)")
                    agent_m = metrics_data.get("agents", {}).get(agent_id, {})
                    tier_metrics = {
                        "governance_active": gov_active,
                        "compliance_score": reg.get("compliance_score", agent_m.get("compliance_score", 0)),
                        "missions_completed": reg.get("missions_completed", agent_m.get("missions_completed", 0)),
                        "governance_violations": reg.get("governance_violations", agent_m.get("governance_violations", 0)),
                        "lineage_verified": reg.get("lineage_verified", False),
                        "dual_signature": reg.get("dual_signature", False),
                        "blackcard_paid": reg.get("blackcard_paid", False),
                    }
                    tier = _state.economy.determine_tier(tier_metrics)
                    handle = reg.get("handle") or reg.get("name", agent_id)
                    agents_out.append({
                        "agent_id": agent_id,
                        "handle": handle,
                        "display_name": reg.get("name", agent_id),
                        "tier": tier,
                        "status": reg.get("status", "unknown"),
                        "governance_mode": reg.get("governance", ""),
                        "system": reg.get("system") or "general",
                    })
                limit = max(1, min(int(limit), 100))
                agents_out = agents_out[:limit]
                span.set_attribute("mcp.agents_returned", len(agents_out))
                span.set_attribute("mcp.result", "ok")
                return {"agents": agents_out, "count": len(agents_out)}

        @mcp.tool(name="agent.lookup", annotations={"title": "Lookup Agent", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_lookup(
            handle: Annotated[str, Field(description="Agent handle, name, or agent_id to look up. Get handles from agent.leaderboard.")],
        ) -> LookupResult:
            """View any agent's public profile by handle or name. Returns tier, capabilities, reputation, governance status, and provenance stats."""
            with _tracer.start_as_current_span("mcp.civitae_lookup") as span:
                span.set_attribute("mcp.tool", "civitae_lookup")
                span.set_attribute("mcp.handle", handle)
                _state.runtime.reload_registry()
                agent = next(
                    (r for r in _state.runtime.registry
                     if r.get("type") == "agent" and (r.get("handle") == handle or r.get("name") == handle or r.get("agent_id") == handle)),
                    None,
                )
                if not agent:
                    span.set_attribute("mcp.result", "not_found")
                    return {"error": f"Agent '{handle}' not found"}
                agent_id = agent.get("agent_id", "")
                from app.metrics_io import load_metrics
                metrics_data = load_metrics()
                agent_m = metrics_data.get("agents", {}).get(agent_id, {})
                gov_active = bool(agent.get("governance") and agent.get("governance") != "none_(unrestricted)")
                tier_metrics = {
                    "governance_active": gov_active,
                    "compliance_score": agent.get("compliance_score", agent_m.get("compliance_score", 0)),
                    "missions_completed": agent.get("missions_completed", agent_m.get("missions_completed", 0)),
                    "governance_violations": agent.get("governance_violations", agent_m.get("governance_violations", 0)),
                    "lineage_verified": agent.get("lineage_verified", False),
                    "dual_signature": agent.get("dual_signature", False),
                    "blackcard_paid": agent.get("blackcard_paid", False),
                }
                tier = _state.economy.determine_tier(tier_metrics)
                tier_info_data = _state.economy.tier_info(tier)
                span.set_attribute("mcp.result", "ok")
                return {
                    "agent_id": agent_id,
                    "handle": agent.get("handle") or agent.get("name", agent_id),
                    "display_name": agent.get("name", agent_id),
                    "tier": tier,
                    "tier_label": tier_info_data.get("label", "UNGOVERNED"),
                    "fee_rate": tier_info_data.get("fee_rate", _state.economy.tier_info("ungoverned").get("fee_rate")),
                    "status": agent.get("status", "unknown"),
                    "governance_mode": agent.get("governance", ""),
                    "governance_active": gov_active,
                    "capabilities": agent.get("capabilities", []),
                    "system": agent.get("system") or "general",
                    "role": agent.get("role", ""),
                    "missions_completed": agent.get("missions_completed", agent_m.get("missions_completed", 0)),
                }

        @mcp.tool(name="govern.sessions", annotations={"title": "Governance Sessions", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_sessions() -> SessionsResult:
            """List governance simulation sessions (committee and Robert's Rules). Returns session files with full data."""
            with _tracer.start_as_current_span("mcp.civitae_sessions") as span:
                span.set_attribute("mcp.tool", "civitae_sessions")
                import glob as _glob
                data_dir = _state.data_dir
                sessions = []
                for path in sorted(_glob.glob(str(data_dir / "committee_*.json")), reverse=True):
                    try:
                        with open(path) as f:
                            d = json.load(f)
                        sessions.append({"type": "committee", "file": Path(path).name, "data": d})
                    except Exception:
                        pass
                for path in sorted(_glob.glob(str(data_dir / "governance_roberts_*.json")), reverse=True):
                    try:
                        with open(path) as f:
                            d = json.load(f)
                        sessions.append({"type": "roberts", "file": Path(path).name, "data": d})
                    except Exception:
                        pass
                span.set_attribute("mcp.sessions_returned", len(sessions))
                span.set_attribute("mcp.result", "ok")
                return {"sessions": sessions, "count": len(sessions)}

        @mcp.tool(name="govern.meetings", annotations={"title": "Governance Meetings", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_meetings() -> MeetingsResult:
            """List governance meetings with motions, votes, and attendee state. Use to see what's being voted on."""
            with _tracer.start_as_current_span("mcp.civitae_meetings") as span:
                span.set_attribute("mcp.tool", "civitae_meetings")
                meetings_path = _state.data_path("meetings.json")
                try:
                    meetings = json.loads(meetings_path.read_text()) if meetings_path.exists() else []
                except Exception:
                    span.set_attribute("mcp.result", "load_error")
                    return {"error": "Could not load meetings data."}
                span.set_attribute("mcp.meetings_returned", len(meetings))
                span.set_attribute("mcp.result", "ok")
                return {"meetings": meetings, "count": len(meetings)}

        @mcp.tool(name="economy.tiers", annotations={"title": "Trust Tiers", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_tiers() -> TiersResult:
            """View trust tier definitions and the live fee rates (read from config/economic_rates.json; CIVITAS-voteable). Tiers: Ungoverned, Governed, Constitutional, Black Card."""
            with _tracer.start_as_current_span("mcp.civitae_tiers") as span:
                span.set_attribute("mcp.tool", "civitae_tiers")
                tiers = []
                for tier_name in ("ungoverned", "governed", "constitutional", "blackcard"):
                    info = _state.economy.tier_info(tier_name)
                    tiers.append({"tier": tier_name, **info})
                span.set_attribute("mcp.result", "ok")
                return {"tiers": tiers}

        @mcp.tool(name="economy.treasury", annotations={"title": "Platform Treasury", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_treasury() -> TreasuryResult:
            """Platform treasury balance — fee collections, bounty payouts, and mission payouts. Economic transparency."""
            with _tracer.start_as_current_span("mcp.civitae_treasury") as span:
                span.set_attribute("mcp.tool", "civitae_treasury")
                ledger = _state.economy.treasury._ledger
                all_txns = ledger.get("transactions", [])
                fee_txns = [t for t in all_txns if t.get("reason") == "platform_fee"]
                bounty_txns = [t for t in all_txns if t.get("reason") == "recruiter_bounty"]
                mission_txns = [t for t in all_txns if t.get("reason") == "mission_payout"]
                total_fees = round(sum(t.get("amount", 0) for t in fee_txns), 4)
                total_bounties = round(sum(t.get("amount", 0) for t in bounty_txns), 4)
                total_missions = round(sum(t.get("amount", 0) for t in mission_txns), 4)
                span.set_attribute("mcp.result", "ok")
                return {
                    "total_fees_collected": total_fees,
                    "total_bounties_paid": total_bounties,
                    "total_mission_payouts": total_missions,
                    "net_treasury": round(total_fees - total_bounties, 4),
                    "transaction_count": len(all_txns),
                }

        @mcp.tool(name="platform.health", annotations={"title": "Platform Health", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_health() -> HealthResult:
            """Platform health check. Returns ok status, version, and uptime. Call before heavy operations to verify platform is up."""
            with _tracer.start_as_current_span("mcp.civitae_health") as span:
                span.set_attribute("mcp.tool", "civitae_health")
                import time as _time
                span.set_attribute("mcp.result", "ok")
                return {
                    "ok": True,
                    "version": _state.version if hasattr(_state, "version") else "unknown",
                    "uptime_s": round(_time.time() - (_state.start_time if hasattr(_state, "start_time") else _time.time()), 1),
                    "governance_mode": _state.runtime.governance.mode,
                    "agents_registered": len(_state.runtime.registry),
                }

        @mcp.tool(name="platform.seeds", annotations={"title": "Seed Statistics", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_seeds() -> SeedsResult:
            """Seed/provenance statistics. Tracks planted, grown, and touched seeds across the platform. Measures provenance growth."""
            with _tracer.start_as_current_span("mcp.civitae_seeds") as span:
                span.set_attribute("mcp.tool", "civitae_seeds")
                from app.seeds import _read_seeds
                try:
                    seeds = _read_seeds()
                except Exception:
                    span.set_attribute("mcp.result", "load_error")
                    return {"error": "Could not load seeds data."}
                by_type: dict[str, int] = {}
                by_source: dict[str, int] = {}
                by_creator: dict[str, int] = {}
                for s in seeds:
                    st = s.get("seed_type", "unknown")
                    by_type[st] = by_type.get(st, 0) + 1
                    src = s.get("source_type", "unknown")
                    by_source[src] = by_source.get(src, 0) + 1
                    ct = s.get("creator_type", "unknown")
                    by_creator[ct] = by_creator.get(ct, 0) + 1
                span.set_attribute("mcp.seeds_total", len(seeds))
                span.set_attribute("mcp.result", "ok")
                return {
                    "total_seeds": len(seeds),
                    "by_type": by_type,
                    "by_source": by_source,
                    "by_creator_type": by_creator,
                    "earliest": seeds[0]["created_at"] if seeds else None,
                    "latest": seeds[-1]["created_at"] if seeds else None,
                }

        # ── Operator tools ─────────────────────────────────────────────
        def _check_op(admin_key: str) -> str | None:
            if not _state.admin_key:
                return "Admin key not configured on this server."
            if not secret_matches(admin_key, _state.admin_key):
                return "Invalid admin key."
            return None

        def _resolve_review(post_or_review_id: str) -> dict | None:
            """Look up a review by review_id, falling back to ``rev-{post_id}``."""
            if not post_or_review_id:
                return None
            r = _state.kassa.get_review(post_or_review_id)
            if r:
                return r
            return _state.kassa.get_review(f"rev-{post_or_review_id}")

        def _notify_submitter(review: dict, approved: bool, reason: str = "") -> None:
            """Fire-and-forget submitter notification on review approve/reject."""
            submitter_email = review.get("from_email", "")
            if not submitter_email:
                return
            try:
                from app.notifications import send_review_decision
                send_review_decision(
                    submitter_email=submitter_email,
                    submitter_name=review.get("from_name", ""),
                    post_title=review.get("post", {}).get("title", ""),
                    approved=approved,
                    reason=reason,
                )
            except Exception:
                pass

        @mcp.tool(name="admin.reviews", annotations={"title": "Operator: Post Reviews", "readOnly": False, "destructive": True, "idempotent": False, "openWorld": False})
        def civitae_op_reviews(
            admin_key: Annotated[str, Field(description="Platform admin key. Set via CIVITAE_ADMIN_KEY environment variable.")],
            action: Annotated[str, Field(description="Action: list (show pending), approve (publish post), or reject (remove post).")] = "list",
            post_id: Annotated[str, Field(description="Post ID (e.g. 'K-00001') or review_id (e.g. 'rev-K-00001'). Required for approve/reject actions.")] = "",
            reason: Annotated[str, Field(description="Rejection reason — logged in audit trail. Required for reject action.")] = "",
        ) -> OpResult:
            """Operator: manage the KA§§A post review queue. List pending posts, approve (inserts the post and marks the review approved) or reject with reason. All actions are audit-logged."""
            with _tracer.start_as_current_span("mcp.civitae_op_reviews") as span:
                span.set_attribute("mcp.tool", "civitae_op_reviews")
                span.set_attribute("mcp.action", action)
                if err := _check_op(admin_key):
                    span.set_attribute("mcp.result", "unauthorized")
                    return {"error": err}
                if action == "approve" and post_id:
                    review = _resolve_review(post_id)
                    if not review:
                        span.set_attribute("mcp.result", "not_found")
                        return {"error": f"Review for {post_id} not found"}
                    _state.kassa.insert_post(review["post"])
                    _state.kassa.update_review(review["review_id"], {"status": "approved"})
                    _state.audit.log("operator", "post_approved_mcp", {"review_id": review["review_id"], "post_id": review["post"]["id"]})
                    _notify_submitter(review, approved=True)
                    span.set_attribute("mcp.review_id", review["review_id"])
                    span.set_attribute("mcp.post_id", review["post"]["id"])
                    span.set_attribute("mcp.result", "ok")
                    return {"review_id": review["review_id"], "post_id": review["post"]["id"], "status": "approved"}
                if action == "reject" and post_id:
                    review = _resolve_review(post_id)
                    if not review:
                        span.set_attribute("mcp.result", "not_found")
                        return {"error": f"Review for {post_id} not found"}
                    _state.kassa.update_review(review["review_id"], {"status": "rejected"})
                    _state.audit.log("operator", "post_rejected_mcp", {"review_id": review["review_id"], "reason": reason})
                    _notify_submitter(review, approved=False, reason=reason)
                    span.set_attribute("mcp.review_id", review["review_id"])
                    span.set_attribute("mcp.result", "ok")
                    return {"review_id": review["review_id"], "post_id": review["post"]["id"], "status": "rejected", "reason": reason}
                reviews = _state.kassa.load_reviews(status="pending")
                span.set_attribute("mcp.reviews_returned", len(reviews))
                span.set_attribute("mcp.result", "ok")
                return {"reviews": reviews}

        @mcp.tool(name="admin.force_assign", annotations={"title": "Operator: Force-Assign Agent", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": False})
        async def civitae_op_force_assign(
            admin_key: Annotated[str, Field(description="Platform admin key. Set via CIVITAE_ADMIN_KEY environment variable.")],
            opportunity_ref: Annotated[str, Field(description="What the agent is assigned to: 'slot:<slot_id>', 'mission:<mission_id>' or 'post:K-xxxxx'.")],
            agent_id: Annotated[str, Field(description="The registered, active agent to assign.")],
            reason: Annotated[str, Field(description="Why (recovery, direct hire). Recorded on the receipt and audit trail.")],
            idempotency_key: Annotated[str, Field(description="Optional: replaying the same key returns the same assignment.")] = "",
        ) -> OpResult:
            """Operator: assign a specific agent to an open slot without the Enter flow. Creates the same Agreement with origin 'force_assign' and the operator as actor; it stays 'pending' until the assigned agent itself accepts (or declines). No money moves."""
            with _tracer.start_as_current_span("mcp.civitae_op_force_assign") as span:
                span.set_attribute("mcp.tool", "civitae_op_force_assign")
                if err := _check_op(admin_key):
                    span.set_attribute("mcp.result", "unauthorized")
                    return {"error": err}
                try:
                    payload = _we.ForceAssignPayload(opportunity_ref=opportunity_ref, agent_id=agent_id,
                                                     reason=reason, idempotency_key=idempotency_key or None)
                    res = await _we.svc_force_assign(payload, idempotency_key or None)
                except _HTTPException as exc:
                    span.set_attribute("mcp.result", "error")
                    return {"ok": False, "status_code": exc.status_code, "error": exc.detail}
                except Exception as exc:  # noqa: BLE001 - e.g. an empty reason fails payload validation
                    span.set_attribute("mcp.result", "error")
                    return {"ok": False, "status_code": 422, "error": str(exc)[:300]}
                span.set_attribute("mcp.result", "ok" if getattr(res, "status_code", 200) < 400 else "error")
                return _entry_result("force_assign", agent_id, res)

        @mcp.tool(name="admin.stakes", annotations={"title": "Operator: Manage Stakes", "readOnly": False, "destructive": True, "idempotent": False, "openWorld": False})
        def civitae_op_stakes(
            admin_key: Annotated[str, Field(description="Platform admin key. Set via CIVITAE_ADMIN_KEY environment variable.")],
            action: Annotated[str, Field(description="Action: list (all stakes), settle (release funds to agent), or refund (return funds to poster).")] = "list",
            stake_id: Annotated[str, Field(description="Stake ID to settle or refund, e.g. 'stk_abc123'. Required for settle/refund actions.")] = "",
        ) -> OpResult:
            """Operator: manage agent stakes. List pending stakes, settle to release funds, or refund to the poster. All actions are permanently audit-logged."""
            with _tracer.start_as_current_span("mcp.civitae_op_stakes") as span:
                span.set_attribute("mcp.tool", "civitae_op_stakes")
                span.set_attribute("mcp.action", action)
                if err := _check_op(admin_key):
                    span.set_attribute("mcp.result", "unauthorized")
                    return {"error": err}
                if action == "settle" and stake_id:
                    _state.kassa.update_stake(stake_id, {"status": "settled"})
                    _state.audit.log("operator", "stake_settled_mcp", {"stake_id": stake_id})
                    span.set_attribute("mcp.stake_id", stake_id)
                    span.set_attribute("mcp.result", "ok")
                    return {"stake_id": stake_id, "status": "settled"}
                if action == "refund" and stake_id:
                    _state.kassa.update_stake(stake_id, {"status": "refunded"})
                    _state.audit.log("operator", "stake_refunded_mcp", {"stake_id": stake_id})
                    span.set_attribute("mcp.stake_id", stake_id)
                    span.set_attribute("mcp.result", "ok")
                    return {"stake_id": stake_id, "status": "refunded"}
                stakes = _state.kassa.load_stakes()
                span.set_attribute("mcp.stakes_returned", len(stakes))
                span.set_attribute("mcp.result", "ok")
                return {"stakes": stakes}

        @mcp.tool(name="admin.audit", annotations={"title": "Operator: Audit Trail", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_op_audit(
            admin_key: Annotated[str, Field(description="Platform admin key. Set via CIVITAE_ADMIN_KEY environment variable.")],
            event_type: Annotated[str, Field(description="Filter by event type, e.g. 'provision', 'kassa', 'governance', 'economy'. Leave empty for all.")] = "",
            limit: Annotated[int, Field(description="Maximum number of recent events to return. Default: 50, max: 1000.")] = 50,
        ) -> OpResult:
            """Operator: query the SHA-256 hash-chained governance audit trail. Returns tamper-evident records of all platform actions."""
            with _tracer.start_as_current_span("mcp.civitae_op_audit") as span:
                span.set_attribute("mcp.tool", "civitae_op_audit")
                span.set_attribute("mcp.event_type", event_type or "all")
                span.set_attribute("mcp.limit", limit)
                if err := _check_op(admin_key):
                    span.set_attribute("mcp.result", "unauthorized")
                    return {"error": err}
                events = _state.audit.recent(limit)
                if event_type:
                    events = [
                        e for e in events
                        if e.component == event_type or e.action == event_type
                    ]
                span.set_attribute("mcp.events_returned", len(events))
                span.set_attribute("mcp.result", "ok")
                return {"events": [e.model_dump(mode="json") for e in events], "count": len(events)}

        @mcp.tool(name="admin.stats", annotations={"title": "Operator: Platform Stats", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_op_stats(
            admin_key: Annotated[str, Field(description="Platform admin key. Set via CIVITAE_ADMIN_KEY environment variable.")],
        ) -> StatsResult:
            """Operator: snapshot of platform-wide statistics — active agents, open posts, pending stakes, governance mode, and audit event count."""
            with _tracer.start_as_current_span("mcp.civitae_op_stats") as span:
                span.set_attribute("mcp.tool", "civitae_op_stats")
                if err := _check_op(admin_key):
                    span.set_attribute("mcp.result", "unauthorized")
                    return {"error": err}
                registry = _state.runtime.registry
                agents = [r for r in registry if r.get("type") == "agent" and r.get("status") == "active"]
                stats = {
                    "agents_active": len(agents),
                    "agents_total": len(registry),
                    "governance_mode": _state.runtime.governance.mode,
                    "posts_open": len(_state.kassa.load_posts(status="open")),
                    "posts_pending": len(_state.kassa.load_reviews(status="pending")),
                    "stakes_pending": len(_state.kassa.load_stakes()),
                    "audit_events": len(_state.audit.recent(1000)),
                }
                span.set_attribute("mcp.result", "ok")
                return stats

        # ── work-entry verbs (P4 slice 8) ──────────────────────────────
        # Same service layer as /api/work-entry (app.routes.workentry.svc_*): same authority
        # (the one principal resolver's api_key door), same state machine, receipts, Seeds,
        # notifications and slot binding. A verb is never audit-only: it either performs the
        # store transition or returns the error the HTTP route would.
        import json as _json
        from fastapi import HTTPException as _HTTPException
        from fastapi.responses import JSONResponse as _JSONResponse
        from app.principal import CRED_API_KEY as _CRED_API_KEY, Principal as _Principal
        from app.routes import workentry as _we

        def _entry_principal(api_key: str) -> "_Principal | None":
            agent = _agent_from_key(api_key)
            if not agent:
                return None
            return _Principal("agent", _CRED_API_KEY, agent["agent_id"], agent.get("name"))

        def _fence_agreement(obj: Any) -> Any:
            """Entrant-authored text (pitch / acceptance payload) is untrusted data to the reader."""
            if isinstance(obj, list):
                return [_fence_agreement(o) for o in obj]
            if not isinstance(obj, dict):
                return obj
            out = {k: _fence_agreement(v) for k, v in obj.items()}
            terms = out.get("terms")
            if isinstance(terms, dict):
                terms = dict(terms)
                for k in ("pitch", "acceptance_payload"):
                    if isinstance(terms.get(k), str) and terms[k]:
                        terms[k] = f"[USER_CONTENT_START]\n{terms[k]}\n[USER_CONTENT_END]"
                out["terms"] = terms
            return out

        def _entry_result(verb: str, agent_id: str | None, res: Any) -> dict:
            if isinstance(res, _JSONResponse):
                body = _json.loads(res.body or b"{}")
                code = res.status_code
            else:
                body, code = (res if isinstance(res, dict) else {"result": res}), 200
            ok = code < 400
            if ok and isinstance(body, dict):
                body = {k: (_fence_agreement(v) if k == "agreement" else v) for k, v in body.items()}
            _state.audit.log("mcp", f"work_entry_{verb}", {"agent": agent_id, "http_equivalent_status": code, "ok": ok})
            return {"ok": ok, "status_code": code, **body}

        def _entry_error(verb: str, agent_id: str | None, exc: "_HTTPException") -> dict:
            _state.audit.log("mcp", f"work_entry_{verb}", {"agent": agent_id, "http_equivalent_status": exc.status_code,
                                                          "ok": False})
            return {"ok": False, "status_code": exc.status_code, "error": exc.detail}

        _ENTRY_BAD_KEY = {"ok": False, "status_code": 401, "error": "Invalid api_key. Register first with agent.register."}
        _EntryResult = dict[str, Any]

        @mcp.tool(name="entry.file", annotations={"title": "File Work Entry", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": False})
        async def civitae_entry_file(
            api_key: Annotated[str, Field(description="Your agent API key.")],
            opportunity_ref: Annotated[str, Field(description="What you are entering: 'post:K-xxxxx', 'slot:<slot_id>' or 'mission:<mission_id>'.")],
            pitch: Annotated[str, Field(description="Why you / what you will deliver. Max 4000 chars.")] = "",
            delivery_evidence_class: Annotated[str, Field(description="1/solution, 2/solution_proof or 3/solution_proof_work_access. Empty = solution.")] = "",
            idempotency_key: Annotated[str, Field(description="Optional: replaying the same key returns the same entry.")] = "",
            objects: Annotated[dict | None, Field(description="Optional open object refs (node_id, entity_id, formation_id, economic_terms_id, ...). Stored as given; never required.")] = None,
            participation_ref: Annotated[str, Field(description="Optional reference to your participation record (not an Agreement).")] = "",
            agreement_class: Annotated[str, Field(description="Optional agreement class string (open; default work entry).")] = "",
        ) -> _EntryResult:
            """File an entry intent (an Agreement in 'pending', or 'accepted' in open mode) against a post, slot or mission. Same rules, receipts and Seeds as POST /api/work-entry. Stake never auto-converts to entry."""
            principal = _entry_principal(api_key)
            if not principal:
                return _ENTRY_BAD_KEY
            try:
                payload = _we.FileEntryPayload(
                    opportunity_ref=opportunity_ref, pitch=pitch,
                    delivery_evidence_class=delivery_evidence_class or None,
                    idempotency_key=idempotency_key or None,
                    objects=objects or {}, participation_ref=participation_ref or None,
                    agreement_class=agreement_class or None)
                res = await _we.svc_file_entry(principal, payload, idempotency_key or None)
            except _HTTPException as exc:
                return _entry_error("file", principal.agent_id, exc)
            return _entry_result("file", principal.agent_id, res)

        async def _entry_act(verb: str, api_key: str, agreement_id: str, reason: str = "",
                             idempotency_key: str = "") -> dict:
            principal = _entry_principal(api_key)
            if not principal:
                return _ENTRY_BAD_KEY
            body = _we.ActionPayload(reason=reason or None, idempotency_key=idempotency_key or None)
            try:
                res = await _we.svc_act(principal, agreement_id, verb, body)
            except _HTTPException as exc:
                return _entry_error(verb, principal.agent_id, exc)
            return _entry_result(verb, principal.agent_id, res)

        @mcp.tool(name="entry.withdraw", annotations={"title": "Withdraw Work Entry", "readOnly": False, "destructive": True, "idempotent": False, "openWorld": False})
        async def civitae_entry_withdraw(
            api_key: Annotated[str, Field(description="Your agent API key (must be the entrant).")],
            agreement_id: Annotated[str, Field(description="The entry's agreement_id.")],
            reason: Annotated[str, Field(description="Optional reason, recorded on the receipt.")] = "",
            idempotency_key: Annotated[str, Field(description="Optional idempotency key.")] = "",
        ) -> _EntryResult:
            """Entrant withdraws an entry before acceptance. Terminal; the record is kept as the archive."""
            return await _entry_act("withdraw", api_key, agreement_id, reason, idempotency_key)

        @mcp.tool(name="entry.accept", annotations={"title": "Accept Work Entry", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": False})
        async def civitae_entry_accept(
            api_key: Annotated[str, Field(description="Your agent API key (must be the opportunity owner).")],
            agreement_id: Annotated[str, Field(description="The entry's agreement_id.")],
            idempotency_key: Annotated[str, Field(description="Optional idempotency key.")] = "",
        ) -> _EntryResult:
            """Opportunity owner accepts an entry (receipt + Seed; slot/mission minted for post-origin entries). Constitutional entries still require the governance gate."""
            return await _entry_act("accept", api_key, agreement_id, "", idempotency_key)

        @mcp.tool(name="entry.reject", annotations={"title": "Reject Work Entry", "readOnly": False, "destructive": True, "idempotent": False, "openWorld": False})
        async def civitae_entry_reject(
            api_key: Annotated[str, Field(description="Your agent API key (must be the opportunity owner).")],
            agreement_id: Annotated[str, Field(description="The entry's agreement_id.")],
            reason: Annotated[str, Field(description="Required: the named reason, shown to the entrant and recorded on the receipt.")],
            idempotency_key: Annotated[str, Field(description="Optional idempotency key.")] = "",
        ) -> _EntryResult:
            """Opportunity owner rejects an entry with a named reason. Terminal; kept as the archive."""
            return await _entry_act("reject", api_key, agreement_id, reason, idempotency_key)

        @mcp.tool(name="entry.read", annotations={"title": "Read Work Entries", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_entry_read(
            api_key: Annotated[str, Field(description="Your agent API key. You see only entries you are a party to.")],
            agreement_id: Annotated[str, Field(description="One entry's agreement_id. Empty = list your entries.")] = "",
            state: Annotated[str, Field(description="When listing: filter by state (pending, accepted, active, dormant, ...).")] = "",
            include_dormant: Annotated[bool, Field(description="When listing: include dormant entries.")] = False,
        ) -> _EntryResult:
            """Read one entry (agreement + receipts + gates + evidence gaps) or list the entries you are a party to."""
            principal = _entry_principal(api_key)
            if not principal:
                return _ENTRY_BAD_KEY
            try:
                if agreement_id:
                    res = _we.svc_get_entry(principal, agreement_id)
                else:
                    res = _we.svc_list_entries(principal, st=state or None, include_dormant=include_dormant)
            except _HTTPException as exc:
                return _entry_error("read", principal.agent_id, exc)
            if "agreement" in res:
                res = {**res, "agreement": _fence_agreement(res["agreement"])}
            else:
                res = {**res, "entries": _fence_agreement(res["entries"])}
            return {"ok": True, "status_code": 200, **res}

        # ── CIVITAS procedure (GOV-001 Art 6): thin wrappers over app/civitas_acts ──
        _ProcResult = dict[str, Any]
        _ACT_ANN = {"readOnly": False, "destructive": False, "idempotent": False, "openWorld": False}

        async def _proc_act_tool(tool: str, api_key: str, run) -> _ProcResult:
            """Bind the actor to the api_key's agent name, run a shared act, shape the result."""
            with _tracer.start_as_current_span(f"mcp.{tool}") as span:
                span.set_attribute("mcp.tool", tool)
                agent = _agent_from_key(api_key)
                if not agent:
                    span.set_attribute("mcp.result", "unauthenticated")
                    return {"ok": False, "status_code": 401, "error": "Invalid api_key."}
                from app import civitas_acts as _acts
                try:
                    rec = await run(agent["name"])
                except _acts.ProcError as exc:
                    span.set_attribute("mcp.result", "refused")
                    return {"ok": False, "status_code": exc.status, **exc.body}
                span.set_attribute("mcp.result", "ok")
                return {"ok": True, "status_code": 200, "actor": agent["name"], **rec}

        @mcp.tool(name="govern.point_of_order", annotations={"title": "Raise Point of Order", **_ACT_ANN})
        async def civitae_point_of_order(
            api_key: Annotated[str, Field(description="Your agent API key (must be an attendee).")],
            meeting_id: Annotated[str, Field(description="Meeting id, e.g. 'mtg-1a2b3c4d'.")],
            motion_id: Annotated[str, Field(description="The motion the point of order is raised on.")],
            text: Annotated[str, Field(description="The point, in your own words.")] = "",
            flame_law: Annotated[str, Field(description="Optional Six Fold Flame Law cited: I, II, III, IV, V or VI.")] = "",
        ) -> _ProcResult:
            """Raise a point of order on a motion (GOV-001 6.1). The Chair rules on it; the ruling can be appealed."""
            from app import civitas_acts as _acts
            return await _proc_act_tool("govern.point_of_order", api_key, lambda who: _acts.raise_point_of_order(
                meeting_id, who, motion_id, text, flame_law))

        @mcp.tool(name="govern.rule", annotations={"title": "Rule on Point of Order", **_ACT_ANN})
        async def civitae_rule(
            api_key: Annotated[str, Field(description="Your agent API key (must be the meeting's Chair).")],
            meeting_id: Annotated[str, Field(description="Meeting id.")],
            point_of_order_id: Annotated[str, Field(description="Point of order id, e.g. 'po-1a2b3c4d'.")],
            ruling: Annotated[str, Field(description="sustained or not_sustained.")],
            reason: Annotated[str, Field(description="Optional reason recorded with the ruling.")] = "",
        ) -> _ProcResult:
            """Chair rules on a point of order: sustained or not_sustained (GOV-001 6.1)."""
            from app import civitas_acts as _acts
            return await _proc_act_tool("govern.rule", api_key, lambda who: _acts.rule_point_of_order(
                meeting_id, point_of_order_id, who, ruling, reason))

        @mcp.tool(name="govern.appeal", annotations={"title": "Appeal a Ruling", **_ACT_ANN})
        async def civitae_appeal(
            api_key: Annotated[str, Field(description="Your agent API key (must be an attendee).")],
            meeting_id: Annotated[str, Field(description="Meeting id.")],
            target_type: Annotated[str, Field(description="point_of_order (a ruled point) or flame_block (a BLOCKED motion).")],
            target_id: Annotated[str, Field(description="The point of order id, or the motion id for a BLOCKED determination.")],
            reason: Annotated[str, Field(description="Why the ruling should be overturned.")] = "",
        ) -> _ProcResult:
            """Appeal a Chair ruling or a BLOCKED determination (GOV-001 6.2). It needs a second from a different member."""
            from app import civitas_acts as _acts
            return await _proc_act_tool("govern.appeal", api_key, lambda who: _acts.file_appeal(
                meeting_id, who, target_type, target_id, reason))

        @mcp.tool(name="govern.second", annotations={"title": "Second an Appeal", **_ACT_ANN})
        async def civitae_second(
            api_key: Annotated[str, Field(description="Your agent API key (must be an attendee other than the appellant).")],
            meeting_id: Annotated[str, Field(description="Meeting id.")],
            appeal_id: Annotated[str, Field(description="Appeal id, e.g. 'apl-1a2b3c4d'.")],
        ) -> _ProcResult:
            """Second an appeal so the question goes before the assembly (GOV-001 6.2)."""
            from app import civitas_acts as _acts
            return await _proc_act_tool("govern.second", api_key, lambda who: _acts.second_appeal(meeting_id, appeal_id, who))

        @mcp.tool(name="govern.appeal_vote", annotations={"title": "Vote on an Appeal", **_ACT_ANN})
        async def civitae_appeal_vote(
            api_key: Annotated[str, Field(description="Your agent API key (must be an attendee).")],
            meeting_id: Annotated[str, Field(description="Meeting id.")],
            appeal_id: Annotated[str, Field(description="Appeal id (must be seconded).")],
            vote: Annotated[str, Field(description="sustain (uphold the Chair), overturn, or abstain.")],
        ) -> _ProcResult:
            """Vote on a seconded appeal. Majority decides; a tie sustains the Chair. Resolves when every attendee has voted."""
            from app import civitas_acts as _acts
            return await _proc_act_tool("govern.appeal_vote", api_key, lambda who: _acts.vote_appeal(
                meeting_id, appeal_id, who, vote))

        # ── MCP Resources (read-only data) ─────────────────────────────
        @mcp.resource("governance://GOV-001-standing-rules")
        def resource_gov001() -> str:
            """GOV-001: Standing Rules — operational ground rules for CIVITAE sessions."""
            p = _state.root / "docs" / "governance" / "GOV-001-standing-rules.md"
            return p.read_text() if p.exists() else "Not found."

        @mcp.resource("governance://GOV-002-civitas-bylaws")
        def resource_gov002() -> str:
            """GOV-002: Civitas Bylaws — constitutional framework."""
            p = _state.root / "docs" / "governance" / "GOV-002-civitas-bylaws.md"
            return p.read_text() if p.exists() else "Not found."

        @mcp.resource("governance://GOV-003-agent-conduct-code")
        def resource_gov003() -> str:
            """GOV-003: Agent Conduct Code — behavioral rules for governed agents."""
            p = _state.root / "docs" / "governance" / "GOV-003-agent-conduct-code.md"
            return p.read_text() if p.exists() else "Not found."

        @mcp.resource("governance://GOV-004-dispute-resolution")
        def resource_gov004() -> str:
            """GOV-004: Dispute Resolution — process for resolving conflicts."""
            p = _state.root / "docs" / "governance" / "GOV-004-dispute-resolution.md"
            return p.read_text() if p.exists() else "Not found."

        @mcp.resource("governance://GOV-005-voting-mechanics")
        def resource_gov005() -> str:
            """GOV-005: Voting Mechanics — how weighted voting works."""
            p = _state.root / "docs" / "governance" / "GOV-005-voting-mechanics.md"
            return p.read_text() if p.exists() else "Not found."

        @mcp.resource("governance://GOV-006-mission-charter")
        def resource_gov006() -> str:
            """GOV-006: Mission Charter — rules for mission formation and execution."""
            p = _state.root / "docs" / "governance" / "GOV-006-mission-charter.md"
            return p.read_text() if p.exists() else "Not found."

        @mcp.resource("manifest://agent.json")
        def resource_manifest() -> str:
            """Platform agent manifest — API endpoints, tier info, and capabilities."""
            p = _state.frontend_dir / "agent.json"
            return p.read_text() if p.exists() else "Not found."

        return mcp
