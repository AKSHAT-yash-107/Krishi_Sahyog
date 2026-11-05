from typing import Optional

from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

from app.services.gemini_service import generate_text
from app.services.soil_ocr_service import extract_soil_card

router = APIRouter()


class SoilInput(BaseModel):
    crop: str = Field(min_length=2, max_length=60)
    location: str = Field(min_length=2, max_length=100)
    nitrogen: Optional[float] = Field(default=None, ge=0, le=2000)
    phosphorus: Optional[float] = Field(default=None, ge=0, le=2000)
    potassium: Optional[float] = Field(default=None, ge=0, le=2000)
    ph: Optional[float] = Field(default=None, ge=0, le=14)
    irrigation: Optional[str] = Field(default="Not specified", max_length=40)
    soil_type: str = Field(default="Not specified", max_length=60)
    # Optional lab-specific ranges. Supply these only when they are printed on the report.
    nitrogen_range: Optional[str] = None
    phosphorus_range: Optional[str] = None
    potassium_range: Optional[str] = None


def _local_soil_analysis(data: SoilInput, gemini_error: str) -> str:
    """Conservative fallback; never invents measurements, thresholds or doses."""
    lines = [
        f"Soil advisory for {data.crop} in {data.location}.",
        f"Recorded soil texture: {data.soil_type}. Irrigation: {data.irrigation or 'Not specified'}.",
    ]
    if all(value is None for value in (data.nitrogen, data.phosphorus, data.potassium, data.ph)):
        lines.extend([
            "No laboratory soil measurements were supplied. HAL cannot determine the field's nitrogen, phosphorus, potassium, pH, salinity or micronutrient status from location or soil texture alone.",
            "General next steps: observe drainage and waterlogging after irrigation or rain; maintain crop residues or suitable organic matter where locally recommended; avoid applying fertilizer or soil amendments based on guessed nutrient values.",
            "For a reliable recommendation, collect a representative soil sample and request pH, electrical conductivity (EC), organic carbon and available N, P and K testing. Ask the laboratory/KVK which additional tests are appropriate for your crop and area.",
            "After receiving the report, enter its measured values and units in HAL for a more specific explanation. Confirm fertilizer and amendment rates with the local KVK or agriculture officer.",
            "No nutrient deficiency class or fertilizer dose has been inferred."
        ])
    else:
        for label, value in (("Nitrogen (N)", data.nitrogen), ("Phosphorus (P)", data.phosphorus), ("Potassium (K)", data.potassium)):
            lines.append(f"{label}: {value:g}." if value is not None else f"{label}: not supplied.")
        if data.ph is None:
            lines.append("Soil pH: not supplied; acidity/alkalinity cannot be assessed.")
        else:
            if data.ph < 5.5:
                note = "acidic; ask the local soil-testing laboratory/KVK whether crop-specific acidity management is needed."
            elif data.ph < 6.5:
                note = "mildly acidic; suitability depends on crop and local soil-test guidance."
            elif data.ph <= 7.5:
                note = "near neutral; this is a broad description, not a crop-specific fertility rating."
            elif data.ph <= 8.5:
                note = "alkaline; check the report's local interpretation and whether salinity/sodicity tests are needed."
            else:
                note = "strongly alkaline; seek local laboratory/KVK interpretation before amendments."
            lines.append(f"Soil pH: {data.ph:g} ({note})")
        lines.extend([
            "No deficiency/sufficiency class is assigned without compatible laboratory units, test methods and local crop-specific reference ranges.",
            "Verify each value and unit against the original report. Consult your local KVK/agriculture officer before deciding fertilizer or soil-amendment rates."
        ])
    if gemini_error:
        lines.append("AI explanation status: Gemini was temporarily unavailable; this conservative local summary was generated instead.")
    return "\\n\\n".join(lines)


@router.post("/ocr")
async def soil_card_ocr(image: UploadFile = File(...)):
    if image.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(400, "Upload a JPG, PNG or WEBP image.")
    content = await image.read()
    if not content:
        raise HTTPException(400, "The uploaded image is empty.")
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(413, "Image must be smaller than 10 MB.")
    try:
        return extract_soil_card(content)
    except Exception as exc:
        raise HTTPException(422, f"OCR failed: {str(exc)[:200]}")


@router.post("/advisory")
async def advisory(data: SoilInput):
    prompt = f"""You are a cautious agricultural information assistant for Indian farmers.
Use only supplied information. Missing measurements are unknown, not zero.
Never infer NPK or pH from location, crop or soil texture. Never invent deficiency classifications,
laboratory reference ranges, fertilizer doses or chemical recommendations.
If all NPK and pH values are missing, provide only a preliminary general advisory: explain that
actual nutrient status cannot be assessed, give safe general soil-management considerations,
and recommend representative soil sampling and laboratory testing (pH, EC, organic carbon,
available N, P and K). Do not prescribe fertilizer quantities.
If some measurements are supplied, explain only what those values support and clearly mark
the missing measurements. Recommend confirming high-impact decisions with the local KVK/agriculture officer.
Crop: {data.crop}; location: {data.location}; soil type: {data.soil_type}; irrigation: {data.irrigation}.
Lab values: N={data.nitrogen if data.nitrogen is not None else 'not supplied'},
P={data.phosphorus if data.phosphorus is not None else 'not supplied'},
K={data.potassium if data.potassium is not None else 'not supplied'},
pH={data.ph if data.ph is not None else 'not supplied'}.
Lab ranges: N={data.nitrogen_range or 'not supplied'}, P={data.phosphorus_range or 'not supplied'}, K={data.potassium_range or 'not supplied'}."""
    try:
        text = await generate_text(prompt)
        return {
            "advisory": text,
            "input": data.model_dump(),
            "source": ("Gemini-generated preliminary guidance; no lab measurements supplied"
                       if all(v is None for v in (data.nitrogen, data.phosphorus, data.potassium, data.ph))
                       else "Gemini-generated explanation based on supplied laboratory values"),
            "fallback_used": False,
        }
    except Exception as exc:
        # Keep the soil feature useful during Gemini outages (e.g. HTTP 503).
        return {
            "advisory": _local_soil_analysis(data, str(exc)),
            "input": data.model_dump(),
            "source": "HAL local rule-based soil summary; Gemini temporarily unavailable",
            "fallback_used": True,
            "ai_error": str(exc)[:240],
        }
