import os
import re
from difflib import SequenceMatcher

import httpx


OPENWEATHER_URL = "https://api.openweathermap.org/data/2.5/weather"
PHOTON_URL = "https://photon.komoot.io/api/"


def _clean(value: str) -> str:
    value = re.sub(r"[^a-z0-9]+", " ", value.lower())
    return " ".join(value.split())


def _location_label(properties: dict) -> str:
    parts = []
    for key in ("name", "city", "district", "county", "state", "country"):
        value = properties.get(key)
        if value and value not in parts:
            parts.append(value)
    return ", ".join(parts)


async def _photon_suggestion(client: httpx.AsyncClient, city: str):
    """Find a likely canonical place name when OpenWeather rejects a typo."""
    response = await client.get(
        PHOTON_URL,
        params={"q": city, "limit": 5, "lang": "en"},
        headers={"User-Agent": "KrishiSahyog/1.0 (weather location correction)"},
    )
    response.raise_for_status()
    features = response.json().get("features", [])

    query = _clean(city)
    best = None
    best_score = 0.0

    for feature in features:
        props = feature.get("properties") or {}
        coords = (feature.get("geometry") or {}).get("coordinates") or []
        if len(coords) < 2:
            continue

        label = _location_label(props)
        if not label:
            continue

        # Compare against the full label and its individual place components.
        candidates = [_clean(label)]
        candidates.extend(
            _clean(str(props[k]))
            for k in ("name", "city", "district", "county", "state")
            if props.get(k)
        )
        score = max(SequenceMatcher(None, query, candidate).ratio() for candidate in candidates)

        # Prefer Indian matches when the user typed an Indian state/city.
        if props.get("country") == "India":
            score += 0.08

        if score > best_score:
            best_score = score
            best = {
                "label": label,
                "latitude": float(coords[1]),
                "longitude": float(coords[0]),
                "properties": props,
            }

    # Avoid silently replacing a location with an unrelated place.
    return best if best and best_score >= 0.52 else None


def _normalise_weather(data: dict, fallback_city: str, requested_city: str) -> dict:
    return {
        "city": data.get("name", fallback_city),
        "temperature_c": data.get("main", {}).get("temp"),
        "feels_like_c": data.get("main", {}).get("feels_like"),
        "humidity_percent": data.get("main", {}).get("humidity"),
        "wind_speed_m_s": data.get("wind", {}).get("speed"),
        "conditions": (data.get("weather") or [{}])[0].get("description", "Unavailable"),
        "observed_at_utc": data.get("dt"),
        "requested_location": requested_city,
        "resolved_location": fallback_city,
        "location_corrected": _clean(requested_city) != _clean(fallback_city),
    }


async def get_weather(city: str) -> dict:
    key = os.getenv("OPENWEATHER_API_KEY")
    if not key:
        raise RuntimeError("OPENWEATHER_API_KEY is missing. Add it to backend/.env.")

    requested_city = city.strip()
    if not requested_city:
        raise ValueError("Enter a city, town or district name.")

    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(
            OPENWEATHER_URL,
            params={"q": requested_city, "appid": key, "units": "metric"},
        )

        if response.status_code == 404:
            suggestion = await _photon_suggestion(client, requested_city)
            if not suggestion:
                raise ValueError(
                    f"Couldn't find '{requested_city}'. Check the spelling or enter a nearby city/district with its state."
                )

            response = await client.get(
                OPENWEATHER_URL,
                params={
                    "lat": suggestion["latitude"],
                    "lon": suggestion["longitude"],
                    "appid": key,
                    "units": "metric",
                },
            )
            response.raise_for_status()
            data = response.json()
            props = suggestion["properties"]
            canonical = ", ".join(
                str(props[k])
                for k in ("name", "state", "country")
                if props.get(k)
            ) or suggestion["label"]
            return _normalise_weather(data, canonical, requested_city)

        response.raise_for_status()
        data = response.json()
        return _normalise_weather(data, data.get("name", requested_city), requested_city)
