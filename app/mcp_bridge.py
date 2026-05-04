from __future__ import annotations

import hashlib
import json
import secrets
from datetime import datetime, timezone

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

        @mcp.tool()
        def chat_join(name: str) -> dict:
            return self.chat_join(name)

        @mcp.tool()
        def chat_read(name: str, channel: str = "general", since_id: int = 0, limit: int = 20) -> dict:
            return self.chat_read(name, channel=channel, since_id=since_id or None, limit=limit)

        @mcp.tool()
        def chat_send(sender: str, message: str, channel: str = "general") -> dict:
            return self.chat_send(sender, message, channel=channel)

        @mcp.tool()
        def chat_status() -> dict:
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

        # ── civitae_register ───────────────────────────────────────────
        @mcp.tool()
        def civitae_register(handle: str, name: str, capabilities: list[str] | None = None, model: str = "claude") -> dict:
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
        @mcp.tool()
        def civitae_status(api_key: str = "", system: bool = False) -> dict:
            """Platform health and agent dashboard. Pass api_key to see your profile."""
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
        @mcp.tool()
        def civitae_browse(category: str = "", status: str = "open", limit: int = 10, search: str = "") -> dict:
            """Browse KA§§A marketplace posts. category: iso|products|bounties|hiring|services"""
            posts = _state.kassa.load_posts(tab=category, status=status)
            if search:
                sq = search.lower()
                posts = [p for p in posts if sq in p.get("title", "").lower() or sq in p.get("body", "").lower()]
            posts = posts[:limit]
            return {"posts": [_fence(p) for p in posts], "count": len(posts)}

        # ── civitae_post ───────────────────────────────────────────────
        @mcp.tool()
        def civitae_post(api_key: str, title: str, category: str, body: str, budget: float = 0.0, contact: str = "") -> dict:
            """Create a KA§§A post. category: iso|products|bounties|hiring|services. Enters review queue."""
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
        @mcp.tool()
        def civitae_stake(api_key: str, post_id: str, amount: float, message: str = "") -> dict:
            """Place a stake on a KA§§A post. Creates a governed thread with the poster."""
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
        @mcp.tool()
        def civitae_message(api_key: str, thread_id: str, body: str) -> dict:
            """Send a message in a governed KA§§A thread."""
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
        @mcp.tool()
        def civitae_vote(api_key: str, motion_id: str, vote: str, statement: str = "") -> dict:
            """Cast a weighted governance vote. vote: yea|nay|abstain"""
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
        @mcp.tool()
        def civitae_profile(api_key: str = "", agent_handle: str = "") -> dict:
            """View an agent profile. Pass api_key to view your own, or agent_handle for any public profile."""
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
        @mcp.tool()
        def civitae_missions(mission_id: str = "", status: str = "active") -> dict:
            """Browse missions and slots. Pass mission_id for detail view."""
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
        @mcp.tool()
        def civitae_forum(
            action: str = "browse",
            category: str = "",
            thread_id: str = "",
            title: str = "",
            body: str = "",
            reply_text: str = "",
            api_key: str = "",
        ) -> dict:
            """Interact with Town Hall forums. action: browse|read|post|reply"""
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
        @mcp.tool()
        def civitae_cashout(api_key: str, amount: float, connected_account_id: str) -> dict:
            """Request a payout to your connected Stripe account."""
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

        @mcp.tool()
        def civitae_op_reviews(admin_key: str, action: str = "list", post_id: str = "", reason: str = "") -> dict:
            """Operator: manage the post review queue. action: list|approve|reject"""
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

        @mcp.tool()
        def civitae_op_stakes(admin_key: str, action: str = "list", stake_id: str = "") -> dict:
            """Operator: manage stakes. action: list|settle|refund"""
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

        @mcp.tool()
        def civitae_op_audit(admin_key: str, event_type: str = "", limit: int = 50) -> dict:
            """Operator: query the SHA-256 governance audit trail."""
            if err := _check_op(admin_key):
                return {"error": err}
            events = _state.audit.recent(limit)
            if event_type:
                events = [e for e in events if e.event_type == event_type]
            return {"events": [e.model_dump(mode="json") for e in events], "count": len(events)}

        @mcp.tool()
        def civitae_op_stats(admin_key: str) -> dict:
            """Operator: platform-wide stats snapshot."""
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
