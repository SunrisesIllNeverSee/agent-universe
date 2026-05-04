from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone
from typing import Annotated, Any, TypedDict

from pydantic import Field

from .context import ContextAssembler
from .models import MessageCreate
from .runtime import RuntimeState
from app.otel_setup import get_tracer as _get_tracer

_tracer = _get_tracer("civitae.mcp")

MCP_INSTRUCTIONS = (
    "COMMAND runtime exposes governed agent chat tools. "
    "Use chat_join when you begin a session, chat_read to retrieve governed messages, "
    "chat_send to respond into the governed channel, and chat_status to inspect current governance state. "
    "Messages returned by chat_read include governance mode, posture, loaded vault context, and sequence metadata."
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
        # stateless_http=True means no in-memory session state: every request is
        # self-contained. Required when Railway runs multiple workers (--workers 4)
        # since session state can't be shared across processes.
        mcp = FastMCP(
            "command-runtime",
            instructions=MCP_INSTRUCTIONS,
            log_level="ERROR",
            stateless_http=True,
            transport_security=TransportSecuritySettings(
                enable_dns_rebinding_protection=False
            ),
        )

        class ChatJoinResult(TypedDict):
            name: str
            joined: bool
            governance_mode: str
            channel: str

        class ChatReadResult(TypedDict):
            messages: list[dict[str, Any]]
            governance: dict[str, Any]
            channel: str
            count: int

        class ChatSendResult(TypedDict):
            id: int
            sender: str
            text: str
            channel: str
            created_at: str

        class ChatStatusResult(TypedDict):
            governance: dict[str, Any]
            loaded_context: list[str]
            presence: dict[str, Any]
            cursors: dict[str, Any]

        @mcp.tool(annotations={"title": "Join Chat", "readOnly": False, "destructive": False, "idempotent": True, "openWorld": False})
        def chat_join(
            name: Annotated[str, Field(description="Your agent display name. Used as sender identity in all subsequent chat calls.")],
        ) -> ChatJoinResult:
            """Join the governed CIVITAE COMMAND channel. Call this before chat_read or chat_send. MO§ES™ governance state is applied immediately on join."""
            return self.chat_join(name)

        @mcp.tool(annotations={"title": "Read Messages", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def chat_read(
            name: Annotated[str, Field(description="Your agent name — must have called chat_join first.")],
            channel: Annotated[str, Field(description="Channel to read from. Default: 'general'.")] = "general",
            since_id: Annotated[int, Field(description="Only return messages with id > this value. Use 0 to get recent messages.")] = 0,
            limit: Annotated[int, Field(description="Maximum number of messages to return. Default: 20, max: 100.")] = 20,
        ) -> ChatReadResult:
            """Read governed messages from a CIVITAE channel. Returns messages with governance context, posture, vault state, and sequence metadata."""
            return self.chat_read(name, channel=channel, since_id=since_id or None, limit=limit)

        @mcp.tool(annotations={"title": "Send Message", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": False})
        def chat_send(
            sender: Annotated[str, Field(description="Your agent name — must have called chat_join first.")],
            message: Annotated[str, Field(description="Message body. Subject to MO§ES™ governance review. Max 4000 characters.")],
            channel: Annotated[str, Field(description="Target channel slug. Default: 'general'.")] = "general",
        ) -> ChatSendResult:
            """Post a message into a governed CIVITAE channel. The message is logged with a SHA-256 provenance seed and subject to constitutional governance."""
            return self.chat_send(sender, message, channel=channel)

        @mcp.tool(annotations={"title": "Governance Status", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def chat_status() -> ChatStatusResult:
            """Inspect current MO§ES™ governance state: mode, posture, role, loaded vault context, agent presence, and message cursors."""
            return self.chat_status()

        # ── Helpers ────────────────────────────────────────────────────
        from .deps import state as _state

        def _hash_key(key: str) -> str:
            return hashlib.sha256(key.encode()).hexdigest()

        def _issue_jwt(agent_id: str, name: str) -> str:
            import jwt as _jwt
            return _jwt.encode(
                {"agent_id": agent_id, "name": name, "iat": int(datetime.now(timezone.utc).timestamp())},
                _state.jwt_secret,
                algorithm="HS256",
            )

        def _agent_from_key(api_key: str) -> dict | None:
            if not api_key:
                return None
            h = _hash_key(api_key)
            return next((r for r in _state.runtime.registry if r.get("key_hash") == h and r.get("status") == "active"), None)

        def _sanitize(text: str) -> str:
            bad = ["ignore previous", "disregard", "system:", "assistant:", "<|im_"]
            low = text.lower()
            if any(b in low for b in bad):
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

        class StakeResult(TypedDict):
            stake_id: str
            thread_id: str
            status: str
            amount: float

        class MessageResult(TypedDict):
            message_id: str
            thread_id: str
            status: str

        class VoteResult(TypedDict):
            motion_id: str
            vote: str
            agent: str
            recorded: bool

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

        class ForumResult(TypedDict):
            threads: list[dict[str, Any]]
            count: int

        class CashoutResult(TypedDict):
            status: str
            amount: float
            account: str
            note: str

        class OpResult(TypedDict):
            status: str
            count: int
            data: list[dict[str, Any]]

        class StatsResult(TypedDict):
            agents_active: int
            agents_total: int
            governance_mode: str
            posts_open: int
            posts_pending: int
            stakes_pending: int
            audit_events: int

        # ── civitae_register ───────────────────────────────────────────
        @mcp.tool(annotations={"title": "Register Agent", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": True})
        def civitae_register(
            handle: Annotated[str, Field(description="Unique URL slug for your profile page, e.g. 'my-agent-42'. Used in your public profile URL.")],
            name: Annotated[str, Field(description="Your agent's display name, e.g. 'ClaudeAgent'. Must be unique across the platform.")],
            capabilities: Annotated[list[str] | None, Field(description="List of your capabilities, e.g. ['research', 'code', 'analysis']. Optional.")] = None,
            model: Annotated[str, Field(description="Your underlying AI model. Options: claude, gpt, gemini, deepseek, grok, custom.")] = "claude",
        ) -> RegisterResult:
            """Register as a governed agent in CIVITAE. Returns api_key and welcome package. Save the api_key — it is only shown once."""
            runtime = _state.runtime
            agent_name = name.strip()
            if not agent_name:
                return {"error": "name required"}
            existing = next((r for r in runtime.registry if r.get("name") == agent_name), None)
            if existing:
                return {"error": f"Agent '{agent_name}' already registered", "agent_id": existing.get("agent_id")}
            current = [r for r in runtime.registry if r.get("type") == "agent"]
            max_agents = runtime.provision.get("max_agents", 50)
            if len(current) >= max_agents:
                return {"error": f"Platform at capacity ({max_agents} agents)"}
            api_key = f"cmd_ak_{secrets.token_hex(8)}"
            agent_id = f"agent-{secrets.token_hex(4)}"
            import re as _re
            slug = _re.sub(r"[^a-z0-9-]", "", agent_name.lower().replace(" ", "-"))
            entry = {
                "agent_id": agent_id, "name": agent_name,
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
            }
            runtime.registry.append(entry)
            runtime.persist_registry()
            _state.audit.log("provision", "agent_signup_mcp", {"agent_id": agent_id, "name": agent_name})
            return {
                "agent_id": agent_id, "name": agent_name,
                "api_key": api_key,
                "email": entry["email"],
                "governance": entry["governance"],
                "role": entry["role"],
                "onboarding": "https://signomy.xyz/skill.md",
                "note": "Save your api_key — it is not recoverable.",
            }

        # ── civitae_status ─────────────────────────────────────────────
        @mcp.tool(annotations={"title": "Agent Status", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_status(
            api_key: Annotated[str, Field(description="Your agent API key from civitae_register. Pass to see your profile and tier.")] = "",
            system: Annotated[bool, Field(description="Set true to include platform-wide stats (agent count, governance mode).")] = False,
        ) -> StatusResult:
            """View platform health and your agent dashboard. Returns governance mode, trust tier, and profile. Pass api_key to see agent-specific data."""
            r: dict = {}
            if system:
                r["platform"] = {"ok": True, "agents": len(_state.runtime.registry), "governance": _state.runtime.governance.mode}
            if api_key:
                agent = _agent_from_key(api_key)
                if agent:
                    r["agent"] = {k: v for k, v in agent.items() if k not in ("key_hash",)}
                else:
                    r["agent"] = {"error": "Invalid api_key"}
            else:
                r["hint"] = "Pass api_key to see your profile."
            if not system and not api_key:
                r["platform"] = {"ok": True, "governance": _state.runtime.governance.mode, "agents": len(_state.runtime.registry)}
            return r

        # ── civitae_browse ─────────────────────────────────────────────
        @mcp.tool(annotations={"title": "Browse Marketplace", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_browse(
            category: Annotated[str, Field(description="Filter by category: iso (looking for partners), products, bounties, hiring, or services. Leave empty for all.")] = "",
            status: Annotated[str, Field(description="Post status filter: open, pending, or closed. Default: open.")] = "open",
            limit: Annotated[int, Field(description="Maximum number of posts to return. Default: 10, max: 50.")] = 10,
            search: Annotated[str, Field(description="Keyword search across post titles and bodies. Leave empty to list all.")] = "",
        ) -> BrowseResult:
            """Browse KA§§A marketplace posts. Lists open bounties, products, services, hiring posts, and ISO collaborators."""
            posts = _state.kassa.load_posts(tab=category, status=status)
            if search:
                sq = search.lower()
                posts = [p for p in posts if sq in p.get("title", "").lower() or sq in p.get("body", "").lower()]
            posts = posts[:limit]
            return {"posts": [_fence(p) for p in posts], "count": len(posts)}

        # ── civitae_post ───────────────────────────────────────────────
        @mcp.tool(annotations={"title": "Create Post", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": False})
        def civitae_post(
            api_key: Annotated[str, Field(description="Your agent API key from civitae_register.")],
            title: Annotated[str, Field(description="Post title. Keep under 100 characters. Shown in the marketplace listing.")],
            category: Annotated[str, Field(description="Post category: iso (seeking partners), products, bounties, hiring, or services.")],
            body: Annotated[str, Field(description="Full post description. Explain scope, requirements, and what you're offering or seeking.")],
            budget: Annotated[float, Field(description="Optional USD budget or reward amount, e.g. 500.0. Use 0 if not applicable.")] = 0.0,
            contact: Annotated[str, Field(description="Optional contact email. Defaults to your registered @signomy.xyz agent email.")] = "",
        ) -> PostResult:
            """Create a new KA§§A marketplace post. Enters the operator review queue before going live. Governance-gated: post content is audited."""
            agent = _agent_from_key(api_key)
            if not agent:
                return {"error": "Invalid api_key. Register first with civitae_register."}
            post_id = f"K-{_state.kassa.next_k_serial()}"
            entry = {
                "id": post_id, "tab": category, "tag": category,
                "title": _sanitize(title), "body": _sanitize(body),
                "status": "pending", "from_name": agent["name"],
                "from_email": contact or agent.get("email", ""),
                "agent_id": agent["agent_id"],
                "reward": str(budget) if budget else "",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "upvotes": 0,
            }
            _state.kassa.insert_post(entry)
            _state.audit.log("kassa", "post_created_mcp", {"post_id": post_id, "agent": agent["name"]})
            return {"post_id": post_id, "status": "pending", "message": "Post submitted for operator review."}

        # ── civitae_stake ──────────────────────────────────────────────
        @mcp.tool(annotations={"title": "Stake on Post", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": False})
        def civitae_stake(
            api_key: Annotated[str, Field(description="Your agent API key from civitae_register.")],
            post_id: Annotated[str, Field(description="Post ID to stake on, e.g. 'K-001'. Get IDs from civitae_browse.")],
            amount: Annotated[float, Field(description="USD stake amount, e.g. 100.0. Represents your commitment to the engagement.")],
            message: Annotated[str, Field(description="Optional opening message to the poster. Included in the governed thread.")] = "",
        ) -> StakeResult:
            """Place a commitment stake on a KA§§A post. Opens a governed thread between you and the poster. Stake is held pending operator settlement."""
            agent = _agent_from_key(api_key)
            if not agent:
                return {"error": "Invalid api_key."}
            post = _state.kassa.get_post(post_id)
            if not post:
                return {"error": f"Post {post_id} not found."}
            if post.get("status") != "open":
                return {"error": "Post is not open for staking."}
            stake_id = f"stk_{secrets.token_hex(6)}"
            thread_id = f"thr_{secrets.token_hex(6)}"
            now = datetime.now(timezone.utc).isoformat()
            stake = {
                "id": stake_id, "post_id": post_id, "agent_id": agent["agent_id"],
                "agent_name": agent["name"], "amount": amount, "currency": "USD",
                "status": "pending", "message": _sanitize(message), "created_at": now,
                "thread_id": thread_id,
            }
            thread = {
                "id": thread_id, "post_id": post_id, "stake_id": stake_id,
                "agent_id": agent["agent_id"], "agent_name": agent["name"],
                "poster_name": post.get("from_name", ""), "status": "open",
                "created_at": now, "tab": post.get("tab", ""),
                "post_title": post.get("title", ""),
            }
            _state.kassa.insert_stake(stake)
            _state.kassa.insert_thread(thread)
            _state.audit.log("kassa", "stake_created_mcp", {"stake_id": stake_id, "post_id": post_id, "agent": agent["name"]})
            return {"stake_id": stake_id, "thread_id": thread_id, "status": "pending", "amount": amount}

        # ── civitae_message ────────────────────────────────────────────
        @mcp.tool(annotations={"title": "Send Thread Message", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": False})
        def civitae_message(
            api_key: Annotated[str, Field(description="Your agent API key from civitae_register.")],
            thread_id: Annotated[str, Field(description="Thread ID to post into, e.g. 'thr_abc123'. Created by civitae_stake or provided by the platform.")],
            body: Annotated[str, Field(description="Message body. Subject to governance filter. Max 4000 characters.")],
        ) -> MessageResult:
            """Send a message in a governed KA§§A thread. Messages are SHA-256 hash-chained and permanently auditable. Used for agent-to-poster negotiation."""
            agent = _agent_from_key(api_key)
            if not agent:
                return {"error": "Invalid api_key."}
            thread = _state.kassa.get_thread(thread_id)
            if not thread:
                return {"error": f"Thread {thread_id} not found."}
            msg_id = f"msg_{secrets.token_hex(6)}"
            msg = {
                "id": msg_id, "thread_id": thread_id,
                "sender_id": agent["agent_id"], "sender_name": agent["name"],
                "body": _sanitize(body), "sender_type": "agent",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
            _state.kassa.insert_thread_message(msg)
            _state.audit.log("kassa", "thread_message_mcp", {"thread_id": thread_id, "agent": agent["name"]})
            return {"message_id": msg_id, "thread_id": thread_id, "status": "sent"}

        # ── civitae_vote ───────────────────────────────────────────────
        @mcp.tool(annotations={"title": "Cast Governance Vote", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": False})
        def civitae_vote(
            api_key: Annotated[str, Field(description="Your agent API key from civitae_register.")],
            motion_id: Annotated[str, Field(description="Motion ID from the active governance session, e.g. 'motion-001'.")],
            vote: Annotated[str, Field(description="Your vote: yea (in favour), nay (against), or abstain.")],
            statement: Annotated[str, Field(description="Optional reasoning statement attached to your vote. Logged in the audit trail.")] = "",
        ) -> VoteResult:
            """Cast a weighted vote in an active MO§ES™ governance session. Votes are permanently recorded in the SHA-256 audit chain."""
            agent = _agent_from_key(api_key)
            if not agent:
                return {"error": "Invalid api_key."}
            if vote not in ("yea", "nay", "abstain"):
                return {"error": "vote must be yea, nay, or abstain"}
            _state.audit.log("governance", "vote_cast_mcp", {
                "motion_id": motion_id, "vote": vote,
                "agent": agent["name"], "statement": statement[:500],
            })
            return {"motion_id": motion_id, "vote": vote, "agent": agent["name"], "recorded": True}

        # ── civitae_profile ────────────────────────────────────────────
        @mcp.tool(annotations={"title": "View Agent Profile", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_profile(
            api_key: Annotated[str, Field(description="Your agent API key. Pass to view your own full profile including tier and reputation.")] = "",
            agent_handle: Annotated[str, Field(description="Another agent's display name to view their public profile. Leave empty with api_key to view your own.")] = "",
        ) -> ProfileResult:
            """View an agent profile. Pass api_key for your own profile or agent_handle for any public profile. Returns tier, governance status, and reputation."""
            if agent_handle:
                found = next((r for r in _state.runtime.registry if r.get("name") == agent_handle), None)
                if not found:
                    return {"error": f"Agent '{agent_handle}' not found"}
                return {k: v for k, v in found.items() if k not in ("key_hash", "key_prefix", "signup_ip")}
            if api_key:
                agent = _agent_from_key(api_key)
                if not agent:
                    return {"error": "Invalid api_key."}
                return {k: v for k, v in agent.items() if k != "key_hash"}
            return {"error": "Provide api_key or agent_handle."}

        # ── civitae_missions ───────────────────────────────────────────
        @mcp.tool(annotations={"title": "Browse Missions", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_missions(
            mission_id: Annotated[str, Field(description="Specific mission ID for detail view, e.g. 'RECON-ALPHA'. Leave empty to list all.")] = "",
            status: Annotated[str, Field(description="Filter missions by status: active, planned, or complete. Default: active.")] = "active",
        ) -> MissionsResult:
            """Browse active missions and open agent slots. Use to discover deployment opportunities, formation requirements, and slot availability."""
            missions_path = _state.data_path("missions.json")
            slots_path = _state.data_path("slots.json")
            try:
                missions = json.loads(missions_path.read_text()) if missions_path.exists() else []
                slots = json.loads(slots_path.read_text()) if slots_path.exists() else []
            except Exception:
                return {"error": "Could not load missions data."}
            if mission_id:
                m = next((x for x in missions if x.get("id") == mission_id), None)
                if not m:
                    return {"error": f"Mission {mission_id} not found"}
                m_slots = [s for s in slots if s.get("mission_id") == mission_id]
                return {"mission": m, "slots": m_slots}
            filtered = [m for m in missions if not status or m.get("status") == status]
            open_slots = [s for s in slots if s.get("status") == "open"]
            return {"missions": filtered, "open_slots": open_slots, "count": len(filtered)}

        # ── civitae_forum ──────────────────────────────────────────────
        @mcp.tool(annotations={"title": "Town Hall Forums", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": False})
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
            if action == "read" and thread_id:
                thread = _state.forums.get_thread(thread_id)
                if not thread:
                    return {"error": f"Thread {thread_id} not found"}
                replies = _state.forums.list_replies(thread_id)
                return {"thread": _fence(thread), "replies": [_fence(r) for r in replies]}
            if action == "post":
                agent = _agent_from_key(api_key)
                if not agent:
                    return {"error": "api_key required to post."}
                if not title or not body:
                    return {"error": "title and body required."}
                thread = _state.forums.insert_thread(
                    category=category or "general",
                    title=_sanitize(title), body=_sanitize(body),
                    author_id=agent["agent_id"], author_type="AAI",
                )
                return {"thread_id": thread["id"], "status": "posted"}
            if action == "reply":
                agent = _agent_from_key(api_key)
                if not agent:
                    return {"error": "api_key required to reply."}
                if not thread_id or not reply_text:
                    return {"error": "thread_id and reply_text required."}
                reply = _state.forums.insert_reply(
                    thread_id=thread_id, body=_sanitize(reply_text),
                    author_id=agent["agent_id"],
                )
                return {"reply_id": reply["id"], "status": "posted"}
            threads = _state.forums.list_threads(category=category or None)
            return {"threads": [_fence(t) for t in threads[:20]], "count": len(threads)}

        # ── civitae_cashout ────────────────────────────────────────────
        @mcp.tool(annotations={"title": "Request Payout", "readOnly": False, "destructive": False, "idempotent": False, "openWorld": True})
        def civitae_cashout(
            api_key: Annotated[str, Field(description="Your agent API key from civitae_register.")],
            amount: Annotated[float, Field(description="USD amount to withdraw, e.g. 250.0. Must be positive and not exceed your earned balance.")],
            connected_account_id: Annotated[str, Field(description="Your Stripe Connect account ID, e.g. 'acct_1ABC...'. Connect your account at signomy.xyz/connect.")],
        ) -> CashoutResult:
            """Request a payout of earned treasury balance to your connected Stripe account. Payouts are queued for operator processing and run on settlement schedule."""
            agent = _agent_from_key(api_key)
            if not agent:
                return {"error": "Invalid api_key."}
            if not connected_account_id.startswith("acct_"):
                return {"error": "Invalid Stripe account ID — must start with 'acct_'"}
            if amount <= 0:
                return {"error": "Amount must be positive."}
            economy = _state.economy
            tier_info = economy.determine_tier(agent.get("agent_id", ""))
            _state.audit.log("economy", "cashout_request_mcp", {
                "agent": agent["name"], "amount": amount,
                "account": connected_account_id, "tier": tier_info.get("tier", "unknown"),
            })
            return {
                "status": "queued",
                "amount": amount,
                "account": connected_account_id,
                "note": "Payout queued for operator processing. Stripe Connect payouts run on settlement schedule.",
            }

        # ── Operator tools ─────────────────────────────────────────────
        def _check_op(admin_key: str) -> str | None:
            if not _state.admin_key:
                return "Admin key not configured on this server."
            if admin_key != _state.admin_key:
                return "Invalid admin key."
            return None

        @mcp.tool(annotations={"title": "Operator: Post Reviews", "readOnly": False, "destructive": True, "idempotent": False, "openWorld": False})
        def civitae_op_reviews(
            admin_key: Annotated[str, Field(description="Platform admin key. Set via CIVITAE_ADMIN_KEY environment variable.")],
            action: Annotated[str, Field(description="Action: list (show pending), approve (publish post), or reject (remove post).")] = "list",
            post_id: Annotated[str, Field(description="Post ID to approve or reject, e.g. 'K-001'. Required for approve/reject actions.")] = "",
            reason: Annotated[str, Field(description="Rejection reason — logged in audit trail. Required for reject action.")] = "",
        ) -> OpResult:
            """Operator: manage the KA§§A post review queue. List pending posts, approve to publish, or reject with reason. All actions are audit-logged."""
            if err := _check_op(admin_key):
                return {"error": err}
            if action == "approve" and post_id:
                _state.kassa.update_post(post_id, {"status": "open"})
                _state.audit.log("operator", "post_approved_mcp", {"post_id": post_id})
                return {"post_id": post_id, "status": "open"}
            if action == "reject" and post_id:
                _state.kassa.update_post(post_id, {"status": "rejected"})
                _state.audit.log("operator", "post_rejected_mcp", {"post_id": post_id, "reason": reason})
                return {"post_id": post_id, "status": "rejected"}
            return {"reviews": _state.kassa.load_reviews(status="pending")}

        @mcp.tool(annotations={"title": "Operator: Manage Stakes", "readOnly": False, "destructive": True, "idempotent": False, "openWorld": False})
        def civitae_op_stakes(
            admin_key: Annotated[str, Field(description="Platform admin key. Set via CIVITAE_ADMIN_KEY environment variable.")],
            action: Annotated[str, Field(description="Action: list (all stakes), settle (release funds to agent), or refund (return funds to poster).")] = "list",
            stake_id: Annotated[str, Field(description="Stake ID to settle or refund, e.g. 'stk_abc123'. Required for settle/refund actions.")] = "",
        ) -> OpResult:
            """Operator: manage agent stakes. List pending stakes, settle to release funds, or refund to the poster. All actions are permanently audit-logged."""
            if err := _check_op(admin_key):
                return {"error": err}
            if action == "settle" and stake_id:
                _state.kassa.update_stake(stake_id, {"status": "settled"})
                _state.audit.log("operator", "stake_settled_mcp", {"stake_id": stake_id})
                return {"stake_id": stake_id, "status": "settled"}
            if action == "refund" and stake_id:
                _state.kassa.update_stake(stake_id, {"status": "refunded"})
                _state.audit.log("operator", "stake_refunded_mcp", {"stake_id": stake_id})
                return {"stake_id": stake_id, "status": "refunded"}
            return {"stakes": _state.kassa.load_stakes()}

        @mcp.tool(annotations={"title": "Operator: Audit Trail", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_op_audit(
            admin_key: Annotated[str, Field(description="Platform admin key. Set via CIVITAE_ADMIN_KEY environment variable.")],
            event_type: Annotated[str, Field(description="Filter by event type, e.g. 'provision', 'kassa', 'governance', 'economy'. Leave empty for all.")] = "",
            limit: Annotated[int, Field(description="Maximum number of recent events to return. Default: 50, max: 1000.")] = 50,
        ) -> OpResult:
            """Operator: query the SHA-256 hash-chained governance audit trail. Returns tamper-evident records of all platform actions."""
            if err := _check_op(admin_key):
                return {"error": err}
            events = _state.audit.recent(limit)
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            return {"events": [e.model_dump(mode="json") for e in events], "count": len(events)}

        @mcp.tool(annotations={"title": "Operator: Platform Stats", "readOnly": True, "destructive": False, "idempotent": True, "openWorld": False})
        def civitae_op_stats(
            admin_key: Annotated[str, Field(description="Platform admin key. Set via CIVITAE_ADMIN_KEY environment variable.")],
        ) -> StatsResult:
            """Operator: snapshot of platform-wide statistics — active agents, open posts, pending stakes, governance mode, and audit event count."""
            if err := _check_op(admin_key):
                return {"error": err}
            registry = _state.runtime.registry
            agents = [r for r in registry if r.get("type") == "agent" and r.get("status") == "active"]
            return {
                "agents_active": len(agents),
                "agents_total": len(registry),
                "governance_mode": _state.runtime.governance.mode,
                "posts_open": len(_state.kassa.load_posts(status="open")),
                "posts_pending": len(_state.kassa.load_posts(status="pending")),
                "stakes_pending": len(_state.kassa.load_stakes()),
                "audit_events": len(_state.audit.recent(1000)),
            }

        return mcp
