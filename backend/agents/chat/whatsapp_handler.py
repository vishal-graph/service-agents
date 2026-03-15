"""
Aadhya – WhatsApp Webhook Handler (Twilio)
Receives messages, routes through ConversationController, sends responses.
"""
from __future__ import annotations
from datetime import datetime
from fastapi import APIRouter, Depends, Form, HTTPException, Request, Response

from backend.config import get_settings
from backend.schemas.session import Session, ConversationStage
from backend.intelligence.conversation_controller import get_controller
from backend.intelligence.persona import OPENING_CHAT_MESSAGE
from backend.storage.redis_store import get_session, save_session
from backend.storage import supabase_store
from backend.agents.chat.twilio_client import twiml_response, send_whatsapp_message
from backend.utils.logger import log_event

router = APIRouter()
_settings = get_settings()


async def _verify_twilio_signature(request: Request) -> None:
    """
    FastAPI dependency that validates the X-Twilio-Signature header.
    If TWILIO_AUTH_TOKEN is not set (local dev), validation is skipped.
    Raises HTTP 403 on tampered/spoofed requests.
    """
    token = _settings.twilio_auth_token
    if not token or token in ("your_twilio_auth_token", ""):
        return  # Skip in local dev / unconfigured environments

    try:
        from twilio.request_validator import RequestValidator
    except ImportError:
        return  # twilio not installed — skip silently

    signature = request.headers.get("X-Twilio-Signature", "")
    url = str(request.url)
    # Twilio passes form data — read it as dict for validation
    form = await request.form()
    params = dict(form)

    validator = RequestValidator(token)
    if not validator.validate(url, params, signature):
        await log_event(
            "SECURITY_VIOLATION",
            session_id="system",
            data={"reason": "invalid_twilio_signature", "url": url},
        )
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")


@router.post("/webhook/whatsapp")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...),
    _: None = Depends(_verify_twilio_signature),
):
    """
    Twilio sends POST with Form fields: From (whatsapp:+91...), Body (message text).
    We return TwiML XML to reply.
    """
    phone_number = From  # e.g. "whatsapp:+919876543210"
    user_message = Body.strip()
    session_id = f"wa_{phone_number}"

    # Load or create session
    session = await get_session(session_id)
    if session is None:
        session = Session(
            session_id=session_id,
            phone_number=phone_number,
            channel="whatsapp",
            conversation_stage=ConversationStage.DISCOVERY,
            created_at=datetime.utcnow(),
            last_active=datetime.utcnow(),
        )
        await log_event("SESSION_START", session_id=session_id,
                        data={"phone": phone_number, "channel": "whatsapp"})

        # Send opening message
        await save_session(session)
        return Response(
            content=twiml_response(OPENING_CHAT_MESSAGE),
            media_type="application/xml",
        )

    # Process message through controller
    controller = get_controller()
    try:
        agent_response = await controller.process_message(
            session=session,
            user_message=user_message,
            channel="whatsapp",
        )
    except Exception as e:
        await log_event("API_ERROR", session_id=session_id,
                        data={"error": str(e), "phase": "whatsapp_handler"})
        fallback = "Could you give me just a moment? I'm just pulling your details together."
        await save_session(session)
        return Response(content=twiml_response(fallback), media_type="application/xml")

    # Persist session
    await save_session(agent_response.session)

    # Persist to Supabase on summary generation
    if agent_response.summary_generated and agent_response.session.summary:
        await supabase_store.save_enquiry(agent_response.session)
        try:
            from backend.schemas.summary import ProjectSummary
            summary_obj = ProjectSummary.model_validate(agent_response.session.summary)
            await supabase_store.save_summary(summary_obj, phone_number=phone_number)
        except Exception:
            pass

    return Response(
        content=twiml_response(agent_response.text),
        media_type="application/xml",
    )
