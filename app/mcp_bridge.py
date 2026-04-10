from __future__ import annotations

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

        import os
        mcp_port = int(os.environ.get("MCP_PORT", "8200"))
        mcp = FastMCP(
            "command-runtime",
            host="127.0.0.1",
            port=mcp_port,
            instructions=MCP_INSTRUCTIONS,
            log_level="ERROR",
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

        return mcp
