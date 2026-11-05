"""
Krishi Sahyog field intelligence engine.

Design principles:
- Deterministic rules own measurements, classifications and risk flags.
- Gemini explains supplied evidence; it does not calculate or invent measurements.
- Missing evidence lowers coverage/confidence, never field health.
- No composite crop-health score is emitted until crop-, stage-, method- and
  region-specific thresholds have been validated.
"""
import asyncio
from datetime import datetime, timezone
from typing import Any

from app.services.weather_service import get_weather
from app.services.satellite_service import analyze_satellite
from app.services.gemini_service import generate_text


def _value(data: Any, name: str, default=None):
    """Read values from either a Pydantic model or a mapping."""
    if isinstance(data, dict):
        return data.get(name, default)
    return getattr(data, name, default)


def _add_indicator(items, domain, name, status, value, interpretation, limitation):
    items.append({
        "domain": domain,
        "indicator": name,
        "status": status,
        "value": value,
        "interpretation": interpretation,
        "limitation": limitation,
    })


def build_rule_report(data, weather, satellite):
    """Build auditable indicators, risks, actions and an evidence-coverage score."""
    indicators = []
    risks = []
    recommendations = []
    missing = []
    evidence = []

    # Context is useful for interpretation, but is not a measured condition.
    crop = _value(data, "crop", "Not specified")
    stage = _value(data, "growth_stage", "Not specified")
    soil_type = _value(data, "soil_type", "Not specified")
    if crop and crop != "Not specified":
        evidence.append({"source": "farmer_input", "field": "crop", "value": crop})
    else:
        missing.append("Crop not specified.")
    if stage and stage != "Not specified":
        evidence.append({"source": "farmer_input", "field": "growth_stage", "value": stage})
    else:
        missing.append("Growth stage not specified.")
    if soil_type and soil_type != "Not specified":
        evidence.append({"source": "farmer_input", "field": "soil_type", "value": soil_type})

    # Soil: pH can be described, but crop-specific suitability is not inferred.
    ph = _value(data, "ph")
    if ph is None:
        missing.append("Soil pH was not supplied.")
    else:
        if ph < 5.5:
            label = "acidic"
        elif ph < 6.5:
            label = "mildly acidic"
        elif ph <= 7.5:
            label = "near neutral"
        elif ph <= 8.5:
            label = "alkaline"
        else:
            label = "strongly alkaline"
        _add_indicator(
            indicators, "soil", "pH", "observed",
            {"value": ph, "unit": "pH"},
            f"Measured pH falls in the {label} descriptive band.",
            "This is a general pH description, not a crop-specific suitability or lime recommendation.",
        )
        evidence.append({"source": "farmer_input", "field": "pH", "value": ph, "unit": "pH"})
        if ph < 5.5 or ph > 8.5:
            risks.append({
                "severity": "review",
                "signal": f"Soil pH is {label}.",
                "reason": f"Reported pH: {ph}.",
                "verification": "Confirm the reading with a laboratory soil test and consult local crop-specific guidance.",
            })
            recommendations.append("Verify soil pH with a laboratory test before considering any amendment.")

    # NPK values are displayed as measurements only. No nutrient status is
    # assigned unless a valid unit, method and crop-specific reference range exist.
    for key, label in (("nitrogen", "Nitrogen"), ("phosphorus", "Phosphorus"), ("potassium", "Potassium")):
        val = _value(data, key)
        ref = _value(data, f"{key}_range")
        if val is None:
            missing.append(f"{label} measurement was not supplied.")
            continue
        _add_indicator(
            indicators, "soil", label, "measurement_only",
            {"value": val, "unit": "not specified"},
            f"Farmer-supplied {label} value recorded.",
            "Cannot classify deficiency or sufficiency without units, test method and a crop-specific laboratory reference range.",
        )
        evidence.append({"source": "farmer_input", "field": key, "value": val, "reference_range": ref})
        if not ref:
            missing.append(f"{label} reference range, unit and test method are unavailable.")
    if any(_value(data, k) is not None for k in ("nitrogen", "phosphorus", "potassium")):
        recommendations.append("Keep the soil laboratory report with NPK units, extraction method and local crop-specific reference ranges for valid nutrient interpretation.")

    # Weather is a current snapshot, not a forecast or seasonal risk model.
    if not weather:
        missing.append("Current weather data is unavailable.")
    else:
        evidence.append({"source": "weather_api", "field": "current_conditions"})
        for key, label, unit in (
            ("temperature_c", "Temperature", "°C"),
            ("humidity_percent", "Relative humidity", "%"),
            ("wind_speed_m_s", "Wind speed", "m/s"),
        ):
            val = weather.get(key)
            if val is not None:
                _add_indicator(
                    indicators, "weather", label, "observed",
                    {"value": val, "unit": unit},
                    f"Current reported {label.lower()}: {val} {unit}.",
                    "Single current observation; not a forecast or crop-stage suitability assessment.",
                )
        humidity = weather.get("humidity_percent")
        if humidity is not None and humidity >= 85:
            risks.append({
                "severity": "watch",
                "signal": "High relative humidity observed.",
                "reason": f"Current reported relative humidity is {humidity}%.",
                "verification": "Inspect the crop canopy for prolonged leaf wetness and disease symptoms; humidity alone does not diagnose disease.",
            })
            recommendations.append("Inspect lower and inner canopy areas for leaf wetness and visible symptoms, especially in dense crop stands.")
        if weather.get("conditions"):
            evidence.append({"source": "weather_api", "field": "conditions", "value": weather["conditions"]})

    # Satellite: preserve the raw indices and compare trend only when possible.
    if not satellite:
        missing.append("Satellite vegetation observations are unavailable or were not requested.")
    else:
        evidence.append({"source": "sentinel_2", "field": "vegetation_indices"})
        indices = satellite.get("indices") or {}
        for key, label in (("ndvi_mean", "Mean NDVI"), ("evi_mean", "Mean EVI")):
            val = indices.get(key)
            if val is not None:
                _add_indicator(
                    indicators, "vegetation", label, "observed",
                    {"value": val, "unit": "index"},
                    f"Satellite-derived field mean {label}: {val}.",
                    "Index values alone do not diagnose nutrient deficiency, disease, yield or crop health.",
                )
        series = satellite.get("timeseries") or []
        valid = [row for row in series if row.get("ndvi_mean") is not None]
        if len(valid) >= 2:
            first, last = valid[0], valid[-1]
            delta = round(float(last["ndvi_mean"]) - float(first["ndvi_mean"]), 4)
            _add_indicator(
                indicators, "vegetation", "NDVI change", "trend_observed",
                {"first_month": first.get("month"), "latest_month": last.get("month"), "change": delta},
                f"NDVI changed by {delta:+.4f} between the first and latest available monthly records.",
                "Trend can reflect crop stage, harvest, soil background, weather, management or image conditions; it is not a diagnosis.",
            )
            if delta <= -0.10:
                risks.append({
                    "severity": "watch",
                    "signal": "Declining vegetation index trend.",
                    "reason": f"NDVI changed by {delta:+.4f} across the available records.",
                    "verification": "Check crop stage, harvest timing, irrigation, field operations and visible crop stress before drawing conclusions.",
                })
                recommendations.append("Compare the satellite dates with sowing, harvest and field-operation records, then inspect the field.")
        else:
            missing.append("At least two valid monthly NDVI observations are needed for a trend comparison.")

    if not risks:
        risks.append({
            "severity": "not_assessed",
            "signal": "No rule-triggered risk signal from the available evidence.",
            "reason": "This does not establish that the field is free of risk.",
            "verification": "Continue routine field scouting and collect missing measurements.",
        })
    if not recommendations:
        recommendations.append("Collect a current soil test and field observations to strengthen the assessment.")

    # This is an evidence completeness indicator, not a probability of correctness
    # or a crop-health score. Weights describe data-source coverage only.
    coverage_parts = [
        {"source": "crop_and_stage_context", "weight": 10, "available": bool(crop and crop != "Not specified" and stage and stage != "Not specified")},
        {"source": "soil_measurements", "weight": 30, "available": any(_value(data, k) is not None for k in ("nitrogen", "phosphorus", "potassium", "ph"))},
        {"source": "current_weather", "weight": 25, "available": bool(weather)},
        {"source": "satellite_observations", "weight": 35, "available": bool(satellite)},
    ]
    confidence = round(sum(x["weight"] for x in coverage_parts if x["available"]))
    return {
        "engine_version": "1.0.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "indicators": indicators,
        "risk_assessment": risks,
        "recommended_checks": recommendations,
        "evidence": evidence,
        "missing_data": missing,
        "data_confidence": {
            "score": confidence,
            "label": "High coverage" if confidence >= 80 else "Moderate coverage" if confidence >= 50 else "Limited coverage",
            "meaning": "Weighted completeness of selected evidence sources only; not model accuracy or crop-health probability.",
            "coverage": coverage_parts,
        },
        "limitations": [
            "No composite crop-health score is calculated because validated crop-, growth-stage-, region- and test-method-specific thresholds are not configured.",
            "NPK values are not classified without units, laboratory method and crop-specific reference ranges.",
            "A current weather snapshot is not a forecast.",
            "NDVI/EVI alone cannot diagnose disease, nutrient deficiency or yield.",
        ],
    }


async def analyze_intelligence(data):
    weather = None
    satellite = None
    module_errors = []

    if _value(data, "fetch_weather", True):
        try:
            weather = await get_weather(_value(data, "location"))
        except Exception as exc:
            module_errors.append({"module": "weather", "error": str(exc)[:250]})

    if _value(data, "fetch_satellite", False):
        try:
            satellite = await asyncio.to_thread(
                analyze_satellite,
                latitude=_value(data, "latitude"),
                longitude=_value(data, "longitude"),
                radius_m=_value(data, "radius_m", 500),
                start_date=_value(data, "start_date"),
                end_date=_value(data, "end_date"),
                max_cloud=_value(data, "max_cloud", 30),
                polygon_geojson=_value(data, "polygon_geojson"),
                crop=_value(data, "crop"),
                growth_stage=_value(data, "growth_stage"),
            )
        except Exception as exc:
            module_errors.append({"module": "satellite", "error": str(exc)[:250]})

    engine = build_rule_report(data, weather, satellite)

    prompt = f"""
You are Krishi Sahyog's agricultural report writer. The deterministic engine
below has already calculated all classifications and risk signals. Explain
them clearly; do not recalculate, override, or invent them.

FARM CONTEXT
Crop: {_value(data, 'crop')}
Location: {_value(data, 'location')}
Growth stage: {_value(data, 'growth_stage')}
Soil type: {_value(data, 'soil_type')}

DETERMINISTIC ENGINE OUTPUT
{engine}

RAW WEATHER DATA
{weather}

RAW SATELLITE DATA
{satellite}

STRICT RULES
- Use only the evidence supplied above.
- Do not invent measurements, rainfall, forecasts, yield estimates or diagnoses.
- Do not assign NPK deficiency classes or fertilizer doses.
- Do not diagnose disease from NDVI/EVI or humidity alone.
- Explain why each risk is flagged and what field check can verify it.
- Explicitly state when data is missing.
- Treat data_confidence as evidence completeness, never as crop health or probability.
- Return Markdown with headings: Field summary, Soil indicators, Weather indicators,
  Vegetation indicators, Risks to verify, Recommended field checks, Data limitations.
"""
    try:
        ai_report = await generate_text(prompt)
        ai_status = "generated"
    except Exception as exc:
        ai_report = (
            "The AI narrative service is unavailable. The deterministic engine "
            "results below remain available; no unsupported recommendations were generated."
        )
        ai_status = "fallback"
        module_errors.append({"module": "gemini", "error": str(exc)[:250]})

    return {
        "crop": _value(data, "crop"),
        "location": _value(data, "location"),
        "growth_stage": _value(data, "growth_stage"),
        "intelligence_report": ai_report,
        "intelligence_engine": engine,
        "rule_engine": {
            "observations": [
                item["interpretation"] for item in engine["indicators"]
            ],
            "warnings": engine["missing_data"],
        },
        "weather": weather,
        "satellite": satellite,
        "ai_status": ai_status,
        "fallback_used": ai_status == "fallback",
        "module_errors": module_errors,
    }
