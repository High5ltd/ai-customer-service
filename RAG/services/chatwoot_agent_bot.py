"""
Handle Chatwoot Agent Bot webhooks: incoming contact message → LLM → reply via Chatwoot API.
"""

import structlog
import httpx

from RAG.config.settings import get_settings
from RAG.services.direct_llm import complete_direct_chat

log = structlog.get_logger()


def _is_incoming_message(message_type: str | int | None) -> bool:
    if message_type is None:
        return False
    if isinstance(message_type, int):
        return message_type == 0
    return str(message_type).lower() == "incoming"


async def process_agent_bot_payload(payload: dict) -> None:
    settings = get_settings()
    base = (settings.chatwoot_base_url or "").strip().rstrip("/")
    token = (settings.chatwoot_bot_token or "").strip()
    if not base or not token:
        log.warning("chatwoot.skip_not_configured")
        return

    if payload.get("event") != "message_created":
        return

    message = payload.get("message") or {}
    conversation = payload.get("conversation") or {}
    account = payload.get("account") or {}

    if message.get("private"):
        return

    if not _is_incoming_message(message.get("message_type")):
        return

    content = (message.get("content") or "").strip()
    if not content:
        return

    account_id = account.get("id")
    conversation_id = conversation.get("id")
    if account_id is None or conversation_id is None:
        log.warning("chatwoot.missing_ids", payload_keys=list(payload.keys()))
        return

    answer = await complete_direct_chat(query=content)

    url = f"{base}/api/v1/accounts/{account_id}/conversations/{conversation_id}/messages"
    async with httpx.AsyncClient(timeout=60.0) as client:
        response = await client.post(
            url,
            headers={"api_access_token": token},
            json={"content": answer, "message_type": "outgoing"},
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
