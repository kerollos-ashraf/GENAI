from dataclasses import asdict
from typing import Annotated

from fastapi import APIRouter, File, UploadFile
from fastapi.concurrency import run_in_threadpool

from app.api.dependencies import AdminOnly, Documents
from app.api.schemas import DocumentInfoOut, DocumentList, SyncResult, TextDocument

router = APIRouter(prefix="/api/v1/documents", tags=["knowledge base"])


@router.get("", response_model=DocumentList)
def list_documents(documents: Documents) -> DocumentList:
    docs = [DocumentInfoOut(**asdict(d)) for d in documents.list()]
    return DocumentList(documents=docs, total_chunks=sum(d.chunks for d in docs))


@router.post("", response_model=SyncResult, status_code=201, dependencies=AdminOnly)
async def upload_document(file: Annotated[UploadFile, File()], documents: Documents) -> SyncResult:
    """Upload a .md / .txt / .pdf file. An existing file with the same name is replaced."""
    data = await file.read(documents.max_bytes + 1)
    report = await run_in_threadpool(documents.add, file.filename or "", data)
    return SyncResult(**report.to_dict())


@router.post("/text", response_model=SyncResult, status_code=201, dependencies=AdminOnly)
async def add_text_document(doc: TextDocument, documents: Documents) -> SyncResult:
    """Add a document from raw text (handy for curl / scripts)."""
    report = await run_in_threadpool(documents.add, doc.filename, doc.content.encode("utf-8"))
    return SyncResult(**report.to_dict())


@router.delete("/{filename}", response_model=SyncResult, dependencies=AdminOnly)
async def delete_document(filename: str, documents: Documents) -> SyncResult:
    report = await run_in_threadpool(documents.delete, filename)
    return SyncResult(**report.to_dict())


@router.post("/reindex", response_model=SyncResult, dependencies=AdminOnly)
async def reindex(documents: Documents, full: bool = False) -> SyncResult:
    """Sync the index with the folder now. `?full=true` rebuilds every embedding."""
    report = await run_in_threadpool(documents.reindex, full)
    return SyncResult(**report.to_dict())
