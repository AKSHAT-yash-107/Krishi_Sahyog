from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from app.services.gemini_service import generate_text

router = APIRouter()

class Question(BaseModel):
    question: str = Field(min_length=3, max_length=1500)
    crop: str = "Not specified"
    location: str = "India"
    soil_context: str = ""
    weather_context: str = ""

@router.post("/ask")
async def ask(data: Question):
    prompt = f"""You are HAL, a helpful agricultural information assistant for Indian farmers.
Answer in simple language. Ask clarifying questions when needed. Never invent local conditions,
guarantee yield, or give unsafe pesticide/fertilizer dosage. Encourage confirmation with a qualified
local agriculture officer for high-impact decisions.
Farmer context: crop={data.crop}; location={data.location};
soil={data.soil_context or 'not provided'}; weather={data.weather_context or 'not provided'}.
Question: {data.question}"""
    try:
        return {"answer": await generate_text(prompt)}
    except Exception as exc:
        raise HTTPException(502, str(exc)[:200])
