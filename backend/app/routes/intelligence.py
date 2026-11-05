
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.intelligence_service import analyze_intelligence

router = APIRouter(
    prefix="/api/intelligence",
    tags=["HAL Intelligence Core"]
)


class IntelligenceInput(BaseModel):
    crop: str = Field(min_length=2, max_length=60)
    location: str = Field(min_length=2, max_length=100)
    growth_stage: str = "Not specified"
    soil_type: str = "Not specified"

    nitrogen: Optional[float] = Field(default=None, ge=0, le=2000)
    phosphorus: Optional[float] = Field(default=None, ge=0, le=2000)
    potassium: Optional[float] = Field(default=None, ge=0, le=2000)
    ph: Optional[float] = Field(default=None, ge=0, le=14)

    nitrogen_range: Optional[str] = None
    phosphorus_range: Optional[str] = None
    potassium_range: Optional[str] = None

    fetch_weather: bool = True
    fetch_satellite: bool = False

    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    radius_m: int = Field(default=500, ge=100, le=5000)

    start_date: Optional[str] = None
    end_date: Optional[str] = None
    max_cloud: float = Field(default=30, ge=0, le=100)

    polygon_geojson: Optional[dict] = None


@router.post("/analyze")
async def intelligence_analysis(data: IntelligenceInput):
    if data.fetch_satellite:
        if data.polygon_geojson is None and (
            data.latitude is None or data.longitude is None
        ):
            raise HTTPException(
                status_code=400,
                detail="Provide a field polygon or latitude and longitude."
            )

    try:
        return await analyze_intelligence(data)
    except Exception as exc:
        print(f"HAL INTELLIGENCE ERROR: {repr(exc)}")
        raise HTTPException(
            status_code=500,
            detail="HAL Intelligence analysis failed."
        )
