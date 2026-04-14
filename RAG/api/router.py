from fastapi import APIRouter

from RAG.api.routes import chat, chatwoot_webhook, direct_llm, documents, health

router = APIRouter()
router.include_router(health.router)
router.include_router(documents.router)
router.include_router(chat.router)
router.include_router(direct_llm.router)
router.include_router(chatwoot_webhook.router)
