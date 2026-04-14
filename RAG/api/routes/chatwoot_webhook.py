import structlog
from fastapi import APIRouter, BackgroundTasks, Request

from RAG.services import chatwoot_agent_bot

router = APIRouter(tags=["chatwoot"])
log = structlog.get_logger()


@router.post("/webhooks/chatwoot")
async def chatwoot_agent_bot_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    URL to register in Chatwoot → Settings → Agent Bots → Webhook URL.
    Requires CHATWOOT_BASE_URL and CHATWOOT_BOT_TOKEN in the environment.
    """
    try:
        payload = await request.json()
    except Exception:
        log.warning("chatwoot.webhook.invalid_json")
        return {"status": "ignored", "reason": "invalid_json"}

    background_tasks.add_task(chatwoot_agent_bot.process_agent_bot_payload, payload)
    return {"status": "accepted"}
