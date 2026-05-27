# 문서 라우터 — Spring AI DocumentController.java 1:1 대응
# POST   /api/v1/rag/documents/upload
# GET    /api/v1/rag/documents?botId=uuid
# GET    /api/v1/rag/documents/{docId}/download
# DELETE /api/v1/rag/documents/{docId}

import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.models.entities import Document
from app.models.schemas import ApiResponse, DocumentResponse
from app.services.document import delete_document, ingest_document

router = APIRouter(prefix="/api/v1/rag/documents", tags=["documents"])


@router.post("/upload", response_model=ApiResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    bot_id: uuid.UUID = Form(...),
    title: str = Form(...),
    file: UploadFile = ...,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """Spring AI: DocumentController.upload() 대응"""
    content = await file.read()
    content_type = file.content_type or "application/octet-stream"

    doc = await ingest_document(
        db=db,
        bot_id=bot_id,
        file_content=content,
        file_name=file.filename or "unknown",
        content_type=content_type,
        title=title,
    )

    return ApiResponse(
        success=True,
        data=DocumentResponse.model_validate(doc).model_dump(),
    )


@router.get("", response_model=ApiResponse)
async def list_documents(
    bot_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """Spring AI: DocumentController.listDocuments() 대응"""
    result = await db.execute(
        select(Document).where(Document.bot_id == bot_id).order_by(Document.created_at.desc())
    )
    docs = result.scalars().all()
    return ApiResponse(
        success=True,
        data=[DocumentResponse.model_validate(d).model_dump() for d in docs],
    )


@router.get("/{doc_id}/download")
async def download_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    """Spring AI: DocumentController.download() 대응"""
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    file_path = Path(settings.upload_dir) / str(doc_id) / doc.file_name
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    return FileResponse(
        path=str(file_path),
        filename=doc.file_name,
        media_type=doc.content_type or "application/octet-stream",
    )


@router.delete("/{doc_id}", response_model=ApiResponse)
async def remove_document(
    doc_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse:
    """Spring AI: DocumentController.delete() 대응"""
    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    await delete_document(db, doc_id)
    return ApiResponse(success=True, message="Document deleted")
