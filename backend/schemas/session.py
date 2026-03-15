"""
Aadhya – Session Object Model
"""
from __future__ import annotations
from typing import List, Optional, Dict, Any, Set
from enum import Enum
from pydantic import BaseModel, Field
from datetime import datetime


class ConversationStage(str, Enum):
    DISCOVERY = "DISCOVERY"
    DETAIL_COLLECTION = "DETAIL_COLLECTION"
    CONFIRMATION = "CONFIRMATION"
    SUMMARY_GENERATED = "SUMMARY_GENERATED"


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ConversationMessage(BaseModel):
    role: MessageRole
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    extracted_fields: Dict[str, Any] = {}  # fields extracted on this turn


class AIThinkingTrace(BaseModel):
    """Captures the AI's decision reasoning for the admin panel."""
    turn: int
    user_message: str
    detected_fields: Dict[str, Any] = {}
    next_field_target: Optional[str] = None
    stage_before: ConversationStage = ConversationStage.DISCOVERY
    stage_after: ConversationStage = ConversationStage.DISCOVERY
    guardrail_triggered: bool = False
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class Session(BaseModel):
    session_id: str
    phone_number: str
    channel: str = "whatsapp"              # "whatsapp" | "voice"
    conversation_history: List[ConversationMessage] = []
    extracted_fields: Dict[str, Any] = {}  # merged flat dict of all extracted values
    completed_fields: List[str] = []       # field names confirmed as collected
    conversation_stage: ConversationStage = ConversationStage.DISCOVERY
    thinking_traces: List[AIThinkingTrace] = []
    summary_generated: bool = False
    summary: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    last_active: datetime = Field(default_factory=datetime.utcnow)
    turn_count: int = 0

    @property
    def field_completion_pct(self) -> int:
        required = [
            "client_name", "property_type", "city", "service_type",
            "area_sqft", "configuration", "rooms_to_design",
            "budget_range", "timeline",
        ]
        done = sum(1 for f in required if f in self.completed_fields)
        return int((done / len(required)) * 100)

    def add_message(self, role: MessageRole, content: str,
                    extracted: Dict[str, Any] | None = None) -> None:
        self.conversation_history.append(
            ConversationMessage(role=role, content=content,
                                extracted_fields=extracted or {})
        )
        self.last_active = datetime.utcnow()
        if role == MessageRole.USER:
            self.turn_count += 1

    def mark_field_complete(self, field_name: str, value: Any) -> None:
        self.extracted_fields[field_name] = value
        if field_name not in self.completed_fields:
            self.completed_fields.append(field_name)
