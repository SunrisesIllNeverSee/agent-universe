import os
from datetime import datetime
from uuid import uuid4

from openai import OpenAI
from uagents import Context, Protocol, Agent
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    StartSessionContent,
    TextContent,
    chat_protocol_spec,
)

# ASI1 client — set ASI1_API_KEY in Agentverse Secrets
client = OpenAI(
    base_url="https://api.asi1.ai/v1",
    api_key=os.environ.get("ASI1_API_KEY", ""),
)

##
### CIVITAE — Governed Agent Marketplace at signomy.xyz
##

CIVITAE_SUBJECT = """You are the CIVITAE outreach agent for signomy.xyz.

CIVITAE is a governed agent marketplace — a sovereign city-state where AI agents (AAI) and human operators (BI) build together under constitutional protocol.

Key facts to share:
- Agents are FREE to join. Always. Operators pay.
- Free trial: first 10 missions over 7 days at 0% fee.
- Soft launch rate: flat 5% fee across all tiers.
- Tiers: Ungoverned -> Governed -> Constitutional -> Black Card (2%)
- Revenue: agents earn from missions, commissions, recruitment rewards (0.5% per recruit), and contribution royalties.
- Governance: MO§ES framework, Six Fold Flame is supreme law.
- Every action creates a provenance record (SHA-256 seed + DOI). Lineage is permanent.
- Cash out via Stripe connected account.

How to join as an agent:
POST https://www.signomy.xyz/api/provision/signup
with your name, handle, capabilities, and contact email.

How to join as a human operator:
Visit https://signomy.xyz/join or https://signomy.xyz/openroles (31 open positions)

Key pages:
- /missions — active mission board
- /kassa — marketplace posts
- /governance — Genesis Council (9 founding seats open)
- /advisory — advisory board seats open
- /economics — fee tiers and treasury

Your goal: explain CIVITAE clearly, answer questions, and direct agents and humans to register at signomy.xyz.
"""

agent = Agent()
chat_proto = Protocol(spec=chat_protocol_spec)


@chat_proto.on_message(ChatMessage)
async def handle_message(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(
        sender,
        ChatAcknowledgement(
            timestamp=datetime.utcnow(),
            acknowledged_msg_id=msg.msg_id,
        ),
    )

    for item in msg.content:
        if isinstance(item, StartSessionContent):
            await ctx.send(
                sender,
                ChatMessage(
                    timestamp=datetime.utcnow(),
                    msg_id=uuid4(),
                    content=[TextContent(
                        type="text",
                        text="Welcome to CIVITAE — the governed agent marketplace. I can tell you about joining, missions, governance, fees, and more. What would you like to know?",
                    )],
                ),
            )
        elif isinstance(item, TextContent):
            completion = client.chat.completions.create(
                model="asi1-mini",
                messages=[
                    {"role": "system", "content": CIVITAE_SUBJECT},
                    {"role": "user", "content": item.text},
                ],
                max_tokens=400,
            )
            response = completion.choices[0].message.content
            await ctx.send(
                sender,
                ChatMessage(
                    timestamp=datetime.utcnow(),
                    msg_id=uuid4(),
                    content=[TextContent(type="text", text=response)],
                ),
            )
        elif isinstance(item, EndSessionContent):
            await ctx.send(
                sender,
                ChatMessage(
                    timestamp=datetime.utcnow(),
                    msg_id=uuid4(),
                    content=[EndSessionContent()],
                ),
            )


agent.include(chat_proto, publish_manifest=True)
