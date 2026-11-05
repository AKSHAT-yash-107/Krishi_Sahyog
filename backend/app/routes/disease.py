from fastapi import APIRouter, UploadFile, File, HTTPException
from app.services.disease_service import classify_leaf
from app.services.gemini_service import generate_text
import base64

router = APIRouter()

@router.post("/classify")
async def classify(image: UploadFile = File(...)):
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(400, "Upload a JPG, PNG, or WEBP image.")
    data = await image.read()
    if not data or len(data) > 8 * 1024 * 1024:
        raise HTTPException(400, "Image must be non-empty and smaller than 8 MB.")
    try:
        result = await classify_leaf(data, image.content_type)
        return result
    except Exception as exc:
        raise HTTPException(502, f"Disease classifier unavailable: {str(exc)[:180]}")
