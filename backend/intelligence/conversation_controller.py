"""
Aadhya – Conversation Controller
Central orchestrator: manages stage transitions, field tracking, guardrails.
Called by both WhatsApp handler and Vapi handler.
"""
from __future__ import annotations
import asyncio
from datetime import datetime
from typing import TYPE_CHECKING

from backend.schemas.session import Session, ConversationStage, MessageRole, AIThinkingTrace
from backend.intelligence.gemini_engine import get_gemini_engine
from backend.intelligence.extractor import get_extractor
from backend.intelligence.enquiry_engine import get_enquiry_engine
from backend.intelligence.persona import (
    get_chat_prompt, get_voice_prompt,
    GUARDRAIL_REDIRECT, BUDGET_REASSURANCE,
)
from backend.summarizer.summary_generator import get_summary_generator
from backend.utils.logger import log_event

# ─── Off-topic guardrail keywords ────────────────────────────────────────────
OFF_TOPIC_KEYWORDS = [
    "stock", "crypto", "bitcoin", "recipe", "weather", "cricket", "movie",
    "exam", "job", "salary", "politics", "news", "visa", "marriage",
    "football", "election", "neet", "jee", "upsc", "dating", "tinder",
]

# ─── Pricing guardrail keywords ──────────────────────────────────────────────
PRICING_KEYWORDS = [
    "how much", "kitna", "price", "cost", "rate", "charges", "per sqft",
    "per square foot", "quote", "estimate", "quotation", "rupee", "rupees",
    "lakh", "lakhs", "budget breakdown", "total cost", "exact price",
    "final price", "billing", "invoice",
]

# ─── Structural / out-of-scope keywords ──────────────────────────────────────
STRUCTURAL_KEYWORDS = [
    "break wall", "remove wall", "load bearing", "structural change",
    "add floor", "extra floor", "demolish", "knock down wall",
    "plumbing riser", "move bathroom", "extend balcony", "build room",
]

# ─── Commitment / promise keywords ───────────────────────────────────────────
COMMITMENT_KEYWORDS = [
    "guarantee", "promise", "how many days", "when will it be done",
    "delivery date", "completion date", "timeline", "deadline", "discount",
    "offer", "free", "complimentary", "how long will it take",
]

# ─── Callback / end-conversation signals ─────────────────────────────────────
CALLBACK_SIGNALS = [
    "i'll discuss with", "let me talk to my", "will get back",
    "need to check with", "call me later", "i'll think about it",
    "not right now", "maybe later", "let me consult",
]

# ─── Gendered title keywords (to avoid) ──────────────────────────────────────
GENDERED_TITLES = ["sir", "ma'am", "madam", "bhai", "didi", "uncle", "aunty", "bro"]


def _is_off_topic(message: str) -> bool:
    lower = message.lower()
    return any(kw in lower for kw in OFF_TOPIC_KEYWORDS)


def _has_budget_anxiety(message: str) -> bool:
    lower = message.lower()
    anxiety_words = ["expensive", "too much", "can't afford", "tight budget",
                     "very low", "no money", "costly", "cheap", "worried about cost"]
    return any(w in lower for w in anxiety_words)


def _is_asking_price(message: str) -> bool:
    lower = message.lower()
    return any(kw in lower for kw in PRICING_KEYWORDS)


def _is_asking_structural(message: str) -> bool:
    lower = message.lower()
    return any(kw in lower for kw in STRUCTURAL_KEYWORDS)


def _is_asking_commitment(message: str) -> bool:
    lower = message.lower()
    return any(kw in lower for kw in COMMITMENT_KEYWORDS)


def _wants_callback(message: str) -> bool:
    lower = message.lower()
    return any(kw in lower for kw in CALLBACK_SIGNALS)


class AgentResponse:
    def __init__(self, text: str, session: Session, summary_generated: bool = False):
        self.text = text
        self.session = session
        self.summary_generated = summary_generated


class ConversationController:
    """
    Orchestrates the conversation lifecycle end-to-end.
    Called with (session, user_message, channel).
    Returns AgentResponse with updated session.
    """

    def __init__(self):
        self.gemini = get_gemini_engine()
        self.extractor = get_extractor()
        self.enquiry = get_enquiry_engine()
        self.summarizer = get_summary_generator()

    async def process_message(
        self,
        session: Session,
        user_message: str,
        channel: str = "whatsapp",
    ) -> AgentResponse:
        """
        Main entry point. Processes one user turn and returns the AI response.
        """
        await log_event("USER_MESSAGE", session_id=session.session_id,
                        data={"message": user_message, "stage": session.conversation_stage})

        # 1. Record user message
        session.add_message(MessageRole.USER, user_message)

        # 2. Guardrail checks
        guardrail_hints = []  # Extra context injected into prompt

        if _is_off_topic(user_message):
            await log_event("GUARDRAIL_TRIGGERED", session_id=session.session_id,
                            data={"user_message": user_message, "reason": "off_topic"})
            session.add_message(MessageRole.ASSISTANT, GUARDRAIL_REDIRECT)
            return AgentResponse(text=GUARDRAIL_REDIRECT, session=session)

        if _wants_callback(user_message):
            await log_event("GUARDRAIL_TRIGGERED", session_id=session.session_id,
                            data={"user_message": user_message, "reason": "callback_requested"})
            guardrail_hints.append(
                "GUARDRAIL ACTIVE: The client wants to end the conversation or discuss with someone. "
                "Do NOT ask more questions. Warmly acknowledge, summarize what you've collected so far, "
                "and let them know the TatvaOps team will follow up."
            )

        if _is_asking_price(user_message):
            await log_event("GUARDRAIL_TRIGGERED", session_id=session.session_id,
                            data={"user_message": user_message, "reason": "pricing_request"})
            guardrail_hints.append(
                "GUARDRAIL ACTIVE: The client is asking about pricing. "
                "Do NOT quote exact prices. You may give very broad ranges if pressed, "
                "and always defer to the project manager for a detailed estimate."
            )

        if _is_asking_structural(user_message):
            await log_event("GUARDRAIL_TRIGGERED", session_id=session.session_id,
                            data={"user_message": user_message, "reason": "structural_scope"})
            guardrail_hints.append(
                "GUARDRAIL ACTIVE: The client is asking about structural/civil changes. "
                "Stay within interior scope. Politely say the design team would need to assess feasibility."
            )

        if _is_asking_commitment(user_message):
            await log_event("GUARDRAIL_TRIGGERED", session_id=session.session_id,
                            data={"user_message": user_message, "reason": "commitment_request"})
            guardrail_hints.append(
                "GUARDRAIL ACTIVE: The client is asking for timelines, guarantees, or discounts. "
                "Do NOT make any commitments on TatvaOps' behalf. Defer to the project manager."
            )

        # Budget anxiety override
        if _has_budget_anxiety(user_message):
            await log_event("GUARDRAIL_TRIGGERED", session_id=session.session_id,
                            data={"user_message": user_message, "reason": "budget_anxiety"})
            guardrail_hints.append(
                "GUARDRAIL ACTIVE: The client is expressing budget anxiety. "
                "Be reassuring: elegance doesn't require extravagance. Mention smart material choices."
            )

        # 3. Extract structured fields from conversation
        new_fields = await self.extractor.extract(
            session_id=session.session_id,
            conversation_history=session.conversation_history,
            gemini_engine=self.gemini,
        )
        newly_completed = self.extractor.merge_into_session(session, new_fields)

        await log_event("NEXT_FIELD_DECISION", session_id=session.session_id,
                        data={
                            "newly_completed": newly_completed,
                            "all_completed": session.completed_fields,
                            "completion_pct": session.field_completion_pct,
                        })

        # 4. Determine stage transitions
        stage_before = session.conversation_stage
        summary_generated = False

        if session.conversation_stage == ConversationStage.DISCOVERY and len(session.completed_fields) >= 2:
            session.conversation_stage = ConversationStage.DETAIL_COLLECTION
            await log_event("STAGE_TRANSITION", session_id=session.session_id,
                            data={"from": stage_before, "to": session.conversation_stage})

        if (session.conversation_stage == ConversationStage.DETAIL_COLLECTION
                and self.enquiry.is_complete(session)):
            session.conversation_stage = ConversationStage.CONFIRMATION
            await log_event("STAGE_TRANSITION", session_id=session.session_id,
                            data={"from": stage_before, "to": session.conversation_stage})

        # Check if user confirmed (simple heuristic on confirmation stage)
        if session.conversation_stage == ConversationStage.CONFIRMATION:
            if any(word in user_message.lower() for word in
                   ["yes", "correct", "right", "looks good", "perfect", "proceed", "go ahead", "confirm"]):
                # Generate summary
                summary = await self.summarizer.generate(session)
                session.summary = summary.model_dump()
                session.summary_generated = True
                session.conversation_stage = ConversationStage.SUMMARY_GENERATED
                summary_generated = True
                await log_event("SUMMARY_GENERATED", session_id=session.session_id,
                                data={"summary_preview": summary.project_overview})

        # 5. Get next field target and build task instruction
        next_field = self.enquiry.get_next_field(session)
        task_instruction = self.enquiry.build_task_instruction(session)

        await log_event("NEXT_FIELD_DECISION", session_id=session.session_id,
                        data={"next_field": next_field, "stage": session.conversation_stage})

        # 6. Build system prompt with context injection
        prompt_fn = get_voice_prompt if channel == "voice" else get_chat_prompt
        system_prompt = prompt_fn(
            stage=session.conversation_stage.value,
            completed_fields=session.completed_fields,
            extracted_fields=session.extracted_fields,
            next_field=next_field,
            task_instruction=task_instruction,
        )

        # 6b. Inject active guardrail hints into the prompt
        if guardrail_hints:
            system_prompt += "\n\n⚠️ ACTIVE GUARDRAILS FOR THIS TURN:\n" + "\n".join(guardrail_hints)

        # 7. Call Gemini
        history = self.gemini.build_history(session.conversation_history[:-1])  # exclude current user msg
        ai_response = await self.gemini.chat(
            session_id=session.session_id,
            user_message=user_message,
            system_prompt=system_prompt,
            history=history,
        )

        # Apply budget reassurance override if anxiety detected
        if _has_budget_anxiety(user_message) and next_field == "budget_range":
            # Prepend reassurance
            ai_response = BUDGET_REASSURANCE

        # 8. Record AI response + thinking trace
        session.add_message(MessageRole.ASSISTANT, ai_response, extracted=new_fields)

        trace = AIThinkingTrace(
            turn=session.turn_count,
            user_message=user_message,
            detected_fields=new_fields,
            next_field_target=next_field,
            stage_before=stage_before,
            stage_after=session.conversation_stage,
        )
        session.thinking_traces.append(trace)

        return AgentResponse(
            text=ai_response,
            session=session,
            summary_generated=summary_generated,
        )


_controller: ConversationController | None = None


def get_controller() -> ConversationController:
    global _controller
    if _controller is None:
        _controller = ConversationController()
    return _controller
