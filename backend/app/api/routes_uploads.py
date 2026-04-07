from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import FileResponse

from app.api.dependencies import require_roles
from app.models.user import User


router = APIRouter(prefix="/uploads", tags=["Uploads"])

ALLOWED_CONTENT_TYPES = {"image/png", "image/jpeg", "image/jpg", "image/webp"}
ALLOWED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}
MAX_FILE_BYTES = 8 * 1024 * 1024
UPLOADS_DIR = Path("uploads")


def _infer_extension(filename: str, content_type: str) -> str:
    ext = Path(filename or "").suffix.lower()
    if ext in ALLOWED_EXTENSIONS:
        return ".jpg" if ext == ".jpeg" else ext

    if content_type in {"image/jpeg", "image/jpg"}:
        return ".jpg"
    if content_type == "image/png":
        return ".png"
    if content_type == "image/webp":
        return ".webp"

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported image type")


@router.post("/image")
async def upload_image(
    request: Request,
    file: UploadFile = File(...),
    current_user: User = Depends(require_roles("farmer", "worker", "customer")),
) -> dict:
    _ = current_user

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only PNG, JPG, or WEBP images are allowed")

    ext = _infer_extension(file.filename or "", file.content_type or "")

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image file is empty")
    if len(payload) > MAX_FILE_BYTES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Image is too large (max 8 MB)")

    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

    fname = f"{uuid4().hex}{ext}"
    out_path = UPLOADS_DIR / fname
    out_path.write_bytes(payload)

    base = str(request.base_url).rstrip("/")
    return {"url": f"{base}/uploads/{fname}"}


@router.get("/{file_name:path}")
def get_uploaded_image(file_name: str) -> FileResponse:
    candidate = (UPLOADS_DIR / file_name).resolve()
    root = UPLOADS_DIR.resolve()

    if root not in candidate.parents and candidate != root:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    if not candidate.is_file():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    return FileResponse(candidate)
