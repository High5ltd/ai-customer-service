from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db.models.document import Document


class DocumentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, **kwargs) -> Document:
        doc = Document(**kwargs)
        self._session.add(doc)
        await self._session.commit()
        await self._session.refresh(doc)
        return doc

    async def get(self, doc_id: str) -> Document | None:
        result = await self._session.execute(select(Document).where(Document.id == doc_id))
        return result.scalar_one_or_none()

    async def list_all(self) -> list[Document]:
        result = await self._session.execute(
            select(Document).order_by(Document.created_at.desc())
        )
        return list(result.scalars().all())

    async def update_status(
        self,
        doc_id: str,
        status: str,
        chunk_count: int = 0,
        error_message: str | None = None,
    ) -> Document | None:
        doc = await self.get(doc_id)
        if doc is None:
            return None
        doc.status = status
        if chunk_count:
            doc.chunk_count = chunk_count
        if error_message is not None:
            doc.error_message = error_message
        await self._session.commit()
        await self._session.refresh(doc)
        return doc

    async def delete(self, doc_id: str) -> bool:
        doc = await self.get(doc_id)
        if doc is None:
            return False
        await self._session.delete(doc)
        await self._session.commit()
        return True
