from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.satellite_service import analyze_satellite

router = APIRouter(prefix="/api/satellite", tags=["Satellite Imagery"])


class SatelliteAnalysisRequest(BaseModel):
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)
    radius_m: int = Field(default=500, ge=100, le=5000)
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    max_cloud: float = Field(default=30, ge=0, le=100)
    polygon_geojson: Optional[dict] = None
    crop: Optional[str] = None
    growth_stage: Optional[str] = None


def _run_analysis(payload):
    try:
        return analyze_satellite(**payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        print(f"SATELLITE API ERROR: {repr(exc)}")
        raise HTTPException(status_code=502, detail=str(exc))


@router.get("/analyze")
def satellite_analysis_get(
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    radius_m: int = Query(500, ge=100, le=5000),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_cloud: float = Query(30, ge=0, le=100),
):
    return _run_analysis({
        "latitude": latitude,
        "longitude": longitude,
        "radius_m": radius_m,
        "start_date": start_date,
        "end_date": end_date,
        "max_cloud": max_cloud,
    })


@router.post("/analyze")
def satellite_analysis_post(payload: SatelliteAnalysisRequest):
    return _run_analysis(payload.dict())
