from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


Role = Literal["primary", "secondary", "observer", "none"]


class SystemConfig(BaseModel):
    id: str
    name: str
    provider: str
    codename: str
    class_name: str = Field(alias="class")
    online: bool = True

    model_config = {"populate_by_name": True}


class AgentConfig(BaseModel):
    name: str
    role: str
    tools: list[str] = Field(default_factory=list)


class GovernanceState(BaseModel):
    mode: str = "None (Unrestricted)"
    posture: str = "SCOUT"
    role: str = "Primary"
    reasoning_mode: str = "Deductive"
    reasoning_depth: str = "MODERATE"
    response_style: str = "Direct"
    output_format: str = "Conversational"
    narrative_strength: float = 0.5
    expertise_level: str = "Expert"
    interaction_mode: str = "Executing"
    domain: str = "General"
    communication_pref: str = "Concise"
    goal: str = "Tactical Execution"


class SystemRuntime(BaseModel):
    active: bool = False
    role: Role = "none"
    seq: int | None = None
    muted: bool = False


class DeployState(BaseModel):
    tab: str = "who"
    systems: dict[str, bool] = Field(default_factory=dict)
    agents: dict[str, bool] = Field(default_factory=dict)
    objective: str = ""
    posture: str = ""
    formation: str = ""
    target: str = ""
    label: str = ""
    duration: str = ""
    limits: str = ""
    active: bool = False


class MessageRecord(BaseModel):
    id: int
    sender: str
    text: str
    timestamp: datetime
    channel: str = "general"
    governance: GovernanceState
    role_context: str = "operator"
    vault_loaded: list[str] = Field(default_factory=list)
    systems: list[str] = Field(default_factory=list)
    meta: dict[str, Any] = Field(default_factory=dict)


class AuditEvent(BaseModel):
    id: int
    timestamp: datetime
    component: str
    action: str
    detail: dict[str, Any] = Field(default_factory=dict)


class RuntimeSnapshot(BaseModel):
    governance: GovernanceState
    systems: dict[str, SystemRuntime]
    loaded_context: list[str]
    deploy: DeployState
    provision: dict[str, Any]
    registry: list[dict[str, Any]]
    agents: list[AgentConfig]
    config_systems: list[SystemConfig]
    vault: dict[str, list[str]]
    recent_messages: list[MessageRecord]
    audit_events: list[AuditEvent]


class MessageCreate(BaseModel):
    sender: str
    text: str
    systems: list[str] = Field(default_factory=list)
    channel: str = "general"
    role_context: str = "operator"
    meta: dict[str, Any] = Field(default_factory=dict)


class GovernanceUpdate(BaseModel):
    mode: str | None = None
    posture: str | None = None
    role: str | None = None
    reasoning_mode: str | None = None
    reasoning_depth: str | None = None
    response_style: str | None = None
    output_format: str | None = None
    narrative_strength: float | None = None
    expertise_level: str | None = None
    interaction_mode: str | None = None
    domain: str | None = None
    communication_pref: str | None = None
    goal: str | None = None


class SystemUpdate(BaseModel):
    system_id: str
    active: bool | None = None
    role: Role | None = None
    seq: int | None = None
    muted: bool | None = None


class VaultSelection(BaseModel):
    file: str


class DeployUpdate(BaseModel):
    tab: str | None = None
    systems: dict[str, bool] | None = None
    agents: dict[str, bool] | None = None
    objective: str | None = None
    posture: str | None = None
    formation: str | None = None
    target: str | None = None
    label: str | None = None
    duration: str | None = None
    limits: str | None = None
    active: bool | None = None


class MCPReadRequest(BaseModel):
    name: str
    channel: str = "general"
    since_id: int = 0
    limit: int = 20


class MCPSendRequest(BaseModel):
    sender: str
    message: str
    channel: str = "general"
    systems: list[str] = Field(default_factory=list)


class KassaContact(BaseModel):
    post_id: str          # e.g. K-00001
    tab: str              # iso | products | bounties | hiring | services
    from_name: str
    from_email: str
    message: str
