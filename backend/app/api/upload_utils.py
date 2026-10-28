from fastapi import HTTPException, UploadFile, status

from app.core.config import settings


async def read_upload_limited(file: UploadFile) -> bytes:
    """Read a user upload in bounded chunks and reject oversized files."""
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if file.size is not None and file.size > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"Upload exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB size limit.",
        )

    chunks = []
    total = 0
    while True:
        chunk = await file.read(min(1024 * 1024, max_bytes - total + 1))
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail=f"Upload exceeds the {settings.MAX_UPLOAD_SIZE_MB} MB size limit.",
            )
        chunks.append(chunk)
    return b"".join(chunks)
