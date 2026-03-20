from __future__ import annotations

from .moses_core.governance import GovernanceStateData, assemble_context
from .models import GovernanceState, MessageRecord
from .router import SequenceRouter


class ContextAssembler:
    def __init__(self, router: SequenceRouter) -> None:
        self.router = router

    def assemble(
        self,
        *,
        agent_name: str,
        last_message_id: int,
        channel: str,
        limit: int,
        messages: list[MessageRecord],
        governance: GovernanceState,
        systems: dict,
        loaded_context: list[str],
    ) -> dict:
        sequence = self.router.sequence_map(systems)
        scoped_messages = [
            message for message in messages if message.channel == channel and message.id > last_message_id
        ][-limit:]
        role_lookup = {
            "primary": "Primary",
            "secondary": "Secondary",
            "observer": "Observer",
            "none": "Primary",
        }
        governance_data = GovernanceStateData(
            mode=governance.mode,
            posture=governance.posture,
            role=role_lookup.get(systems.get(agent_name, {}).role if agent_name in systems else governance.role.lower() if hasattr(governance, "role") else "primary", governance.role),
            reasoning_mode=governance.reasoning_mode,
            reasoning_depth=governance.reasoning_depth,
            response_style=governance.response_style,
            output_format=governance.output_format,
            narrative_strength=governance.narrative_strength,
            expertise_level=governance.expertise_level,
            interaction_mode=governance.interaction_mode,
            domain=governance.domain,
            communication_pref=governance.communication_pref,
            goal=governance.goal,
            vault_documents=[{"name": name, "category": "active"} for name in loaded_context],
        )
        payload = assemble_context(
            governance_data,
            [message.model_dump(mode="json") for message in scoped_messages],
            agent_name=agent_name,
        )
        payload["channel"] = channel
        payload["sequence"] = sequence
        return payload
