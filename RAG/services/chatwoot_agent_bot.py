"""
Handle Chatwoot Agent Bot webhooks: incoming contact message → LLM → reply via Chatwoot API.
"""

import httpx
import structlog

from RAG.config.settings import get_settings
from RAG.services.direct_llm import complete_direct_chat

log = structlog.get_logger()


def _is_incoming_message(message_type: str | int | None) -> bool:
    if message_type is None:
        return False
    if isinstance(message_type, int):
        return message_type == 0
    s = str(message_type).lower()
    if s == "incoming":
        return True
    if s.isdigit():
        return int(s) == 0
    return False


def _split_webhook_payload(payload: dict) -> tuple[dict, dict, dict]:
    """
    Chatwoot sends message_created either:
    - nested: payload["message"] is a full message object, or
    - flat: content / message_type / conversation / account live on the root (user guide sample).
    """
    nested = payload.get("message")
    if isinstance(nested, dict) and nested:
        message = nested
        mc = message.get("conversation")
        if isinstance(mc, dict):
            conversation = mc
        else:
            pc = payload.get("conversation")
            conversation = pc if isinstance(pc, dict) else {}
        pa, ma = payload.get("account"), message.get("account")
        if isinstance(pa, dict):
            account = pa
        elif isinstance(ma, dict):
            account = ma
        else:
            account = {}
        return message, conversation, account

    message = payload
    conv = payload.get("conversation")
    conversation = conv if isinstance(conv, dict) else {}
    acct = payload.get("account")
    account = acct if isinstance(acct, dict) else {}
    return message, conversation, account


def _conversation_api_id(conversation: dict) -> int | None:
    """REST API path uses numeric conversation id; fallback to display_id if present."""
    for key in ("id", "display_id"):
        raw = conversation.get(key)
        if raw is None:
            continue
        try:
            return int(raw)
        except (TypeError, ValueError):
            continue
    return None


async def process_agent_bot_payload(payload: dict) -> None:
    try:
        await _process_agent_bot_payload_inner(payload)
    except Exception:
        log.exception("chatwoot.webhook_task_failed")


async def _process_agent_bot_payload_inner(payload: dict) -> None:
    settings = get_settings()
    base = (settings.chatwoot_base_url or "").strip().rstrip("/")
    token = (settings.chatwoot_bot_token or "").strip()
    if not base or not token:
        log.warning("chatwoot.skip_not_configured")
        return

    event = payload.get("event")
    if event != "message_created":
        log.debug("chatwoot.event_ignored", webhook_event=event)
        return

    message, conversation, account = _split_webhook_payload(payload)

    if message.get("private"):
        return

    mt = message.get("message_type")
    if not _is_incoming_message(mt):
        log.debug("chatwoot.skip_non_incoming", message_type=mt)
        return

    content = (message.get("content") or "").strip()
    if not content:
        log.debug("chatwoot.skip_empty_content")
        return

    account_id = account.get("id")
    conversation_id = _conversation_api_id(conversation)
    if account_id is None or conversation_id is None:
        log.warning(
            "chatwoot.missing_ids",
            account_id=account_id,
            conversation_id=conversation_id,
            conversation_keys=list(conversation.keys()) if conversation else [],
        )
        return

    try:
        account_id = int(account_id)
    except (TypeError, ValueError):
        log.warning("chatwoot.bad_account_id", account_id=account_id)
        return

    answer = await complete_direct_chat(query=content)

    url = f"{base}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            headers={"api_access_token": token},
            json={
                "content": answer,
                "message_type": "outgoing",
                "private": False,
                "content_type": "text",
            },
        )

    if response.is_success:
        log.info(
            "chatwoot.reply_sent",
            conversation_id=conversation_id,
            answer_len=len(answer),
        )
    else:
        log.error(
            "chatwoot.reply_failed",
            status_code=response.status_code,
            body=response.text[:800],
        )
