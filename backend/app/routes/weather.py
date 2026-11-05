from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.weather_service import get_weather
from app.services.gemini_service import generate_text

router = APIRouter()


class WeatherInput(BaseModel):
    city: str = Field(min_length=2, max_length=100)
    crop: str = Field(min_length=2, max_length=60)
    growth_stage: str = "Not specified"


@router.post("/advisory")
async def advisory(data: WeatherInput):
    try:
        weather = await get_weather(data.city)
        prompt = f"""You are a cautious agricultural advisor. Based on this actual weather snapshot, give short,
conditional precautions for the stated crop. Do not claim to know soil moisture, rainfall totals, or forecast
unless present in the data. State that this is general guidance, not an official local advisory.
Crop: {data.crop}; growth stage: {data.growth_stage}; location: {weather.get('resolved_location', data.city)}.
Weather: {weather}"""
        advice = await generate_text(prompt)
        return {
            "weather": weather,
            "advisory": advice,
            "location_correction": (
                {
                    "requested": weather.get("requested_location"),
                    "resolved": weather.get("resolved_location"),
                }
                if weather.get("location_corrected")
                else None
            ),
        }
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)[:200])
