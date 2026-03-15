"""
Aadhya – Vapi Voice Webhook Handler
Processes Vapi call events and routes through the ConversationController.
"""
from __future__ import annotations
from datetime import datetime
from typing import Any
from fastapi import APIRouter, Request, HTTPException

from backend.schemas.session import Session, ConversationStage
from backend.intelligence.conversation_controller import get_controller
from backend.intelligence.persona import OPENING_VOICE_MESSAGE
from backend.storage.redis_store import get_session, save_session
from backend.storage import supabase_store
from backend.agents.voice.voice_response_optimizer import optimize_for_voice
from backend.utils.logger import log_event

router = APIRouter()


@router.post("/webhook/vapi")
async def vapi_webhook(request: Request):
    """
    Vapi sends JSON POST with a 'message' object.
    We handle transcript events and return assistant.say responses.
    """
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    message = body.get("message", {})
    msg_type = message.get("type", "")

    # ─── Handle call start ────────────────────────────────────────────────
    if msg_type == "assistant-request":
        # Vapi is asking for assistant config — return our ElevenLabs voice config
        return _assistant_config_response(OPENING_VOICE_MESSAGE)

    # ─── Handle transcripts ───────────────────────────────────────────────
    if msg_type == "transcript":
        role = message.get("role", "")
        transcript = message.get("transcript", "").strip()

        if role != "user" or not transcript:
            return {"results": []}

        # Build session ID from call data
        call = body.get("call", {})
        call_id = call.get("id", "unknown_call")
        phone = call.get("customer", {}).get("number", call_id)
        session_id = f"voice_{call_id}"

        # Load or create session
        session = await get_session(session_id)
        if session is None:
            session = Session(
                session_id=session_id,
                phone_number=phone,
                channel="voice",
                conversation_stage=ConversationStage.DISCOVERY,
                created_at=datetime.utcnow(),
                last_active=datetime.utcnow(),
            )
            await log_event("SESSION_START", session_id=session_id,
                            data={"phone": phone, "channel": "voice"})

        # Route through controller
        controller = get_controller()
        try:
            agent_response = await controller.process_message(
                session=session,
                user_message=transcript,
                channel="voice",
            )
        except Exception as e:
            await log_event("API_ERROR", session_id=session_id,
                            data={"error": str(e), "phase": "vapi_handler"})
            fallback = "Could you give me just a moment, I'm pulling up your details."
            await save_session(session)
            return _say_response(fallback)

        # Optimize for voice
        voice_text = optimize_for_voice(agent_response.text)

        # Persist
        await save_session(agent_response.session)

        if agent_response.summary_generated and agent_response.session.summary:
            await supabase_store.save_enquiry(agent_response.session)
            try:
                from backend.schemas.summary import ProjectSummary
                summary_obj = ProjectSummary.model_validate(agent_response.session.summary)
                await supabase_store.save_summary(summary_obj, phone_number=phone)
            except Exception:
                pass

        return _say_response(voice_text)

    # ─── Handle end-of-call ───────────────────────────────────────────────
    if msg_type == "end-of-call-report":
        call = body.get("call", {})
        call_id = call.get("id", "unknown")
        session_id = f"voice_{call_id}"
        await log_event("CALL_ENDED", session_id=session_id,
                        data={"event": "call_ended", "call_id": call_id})
        return {"status": "ok"}

    return {"results": []}


def _say_response(text: str) -> dict:
    """Vapi response format to make the assistant speak."""
    return {
        "results": [{
            "toolCallId": "aadhya_response",
            "result": text,
        }]
    }


def _assistant_config_response(opening_message: str) -> dict:
    """
    Returns Vapi assistant configuration.
    This is sent when Vapi first establishes a call.
    """
    from backend.config import get_settings
    s = get_settings()
    return {
        "assistant": {
            "firstMessage": opening_message,
            "voice": {
                "provider": "11labs",
                "voiceId": s.elevenlabs_voice_id or "EXAVITQu4vr4xnSDxMaL",  # Default: Bella
                "stability": 0.6,
                "similarityBoost": 0.85,
            },
            "transcriber": {
                "provider": "deepgram",
                "model": "nova-2",
                "language": "en-IN",
            },
            "model": {
                "provider": "custom-llm",
                "url": f"{s.base_url.rstrip('/')}/webhook/vapi",
            },
            "endCallMessage": "Thank you for speaking with me. Our team will be in touch with your design brief soon. Have a wonderful day!",
            "endCallPhrases": ["goodbye", "bye", "that's all", "thank you bye", "ok thanks bye"],
        }
    }
