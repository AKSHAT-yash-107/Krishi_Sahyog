"""Local Agriculture Marketing dataset service for HAL Lite.

Set HAL_MANDI_DB to the SQLite database path, or use backend/data/mandi_data.sqlite3.
No live AGMARKNET price API is called by this module.
"""
import math
import os
import sqlite3
from datetime import date, datetime, timezone
from pathlib import Path

import httpx

DB_PATH = Path(os.getenv(
    "HAL_MANDI_DB",
    str(Path(__file__).resolve().parents[2] / "data" / "mandi_data.sqlite3")
)).expanduser().resolve()


def _connect():
    if not DB_PATH.is_file():
        raise FileNotFoundError(
            f"Local mandi database not found at {DB_PATH}. "
            "Run scripts/import_mandi_csv.py first."
        )
    con = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, timeout=30)
    con.row_factory = sqlite3.Row
    return con


def _freshness_label(age):
    if age is None:
        return "unknown"
    if age <= 2:
        return "recent"
    if age <= 7:
        return "delayed"
    return "historical"


def _date_age(value):
    try:
        return (date.today() - date.fromisoformat(value)).days
    except (TypeError, ValueError):
        return None


def _row_to_record(row):
    modal = row["modal_price"]
    return {
        "state": row["state_name"],
        "district": row["district_name"],
        "market": row["market_center_name"],
        "market_id": str(row["market_center_code"] or ""),
        "commodity": row["commodity_name"],
        "variety": row["variety"] or "",
        "grade": row["grade"] or "",
        "date": row["date"],
        "arrival_quantity": row["arrival_quantity"],
        "arrival_units": row["arrival_units"],
        "min_price": row["min_price"],
        "max_price": row["max_price"],
        "modal_price": modal,
        "reported": isinstance(modal, (int, float)) and modal > 0,
        "price_unit": row["price_unit"],
        "latitude": row["latitude"],
        "longitude": row["longitude"],
    }


async def get_mandi_filter_options():
    with _connect() as con:
        states = [{"id": str(r["state_name"]), "name": r["state_name"]}
                  for r in con.execute("SELECT DISTINCT state_name FROM mandi_prices WHERE state_name<>'' ORDER BY state_name")]
        districts = [{"id": str(r["district_name"]), "state_id": str(r["state_name"]), "name": r["district_name"]}
                     for r in con.execute("SELECT DISTINCT state_name,district_name FROM mandi_prices WHERE district_name<>'' ORDER BY state_name,district_name")]
        commodities = [{"id": str(r["commodity_name"]), "name": r["commodity_name"]}
                       for r in con.execute("SELECT DISTINCT commodity_name FROM mandi_prices WHERE commodity_name<>'' ORDER BY commodity_name")]
        varieties = [{"id": str(r["variety"]), "commodity_id": str(r["commodity_name"]), "name": r["variety"]}
                     for r in con.execute("SELECT DISTINCT commodity_name,variety FROM mandi_prices WHERE variety<>'' ORDER BY commodity_name,variety")]
    return {"source": "Agriculture Marketing dataset (local CSV)", "states": states,
            "districts": districts, "commodities": commodities, "varieties": varieties}


async def get_mandi_prices(state, commodity, district="", market="", variety="", limit=25, offset=0):
    if not state or not commodity:
        raise ValueError("State and commodity are required.")
    limit = max(1, min(int(limit), 100))
    offset = max(0, int(offset))
    clauses = ["state_name = ?", "commodity_name = ?"]
    params = [state, commodity]
    if district:
        clauses.append("district_name = ?")
        params.append(district)
    if market:
        clauses.append("market_center_name = ?")
        params.append(market)
    if variety:
        clauses.append("variety = ?")
        params.append(variety)
    where = " AND ".join(clauses)
    with _connect() as con:
        total = con.execute(f"SELECT COUNT(*) FROM mandi_prices WHERE {where}", params).fetchone()[0]
        rows = con.execute(
            f"""SELECT * FROM mandi_prices WHERE {where}
                ORDER BY date DESC, market_center_name, variety
                LIMIT ? OFFSET ?""",
            (*params, limit, offset)
        ).fetchall()
    records = [_row_to_record(r) for r in rows]
    reported_dates = [r["date"] for r in records if r["reported"]]
    latest = max(reported_dates) if reported_dates else None
    age = _date_age(latest)
    return {
        "source": "Agriculture Marketing dataset (local CSV)",
        "endpoint": "local_sqlite",
        "filters": {"state": state, "district": district or None, "market": market or None,
                    "commodity": commodity, "variety": variety or None},
        "total_records": total,
        "records": records,
        "record_count": len(records),
        "reported_record_count": sum(1 for r in records if r["reported"]),
        "latest_arrival_date": latest,
        "data_age_days": age,
        "data_freshness": _freshness_label(age),
        "pagination": {"limit": limit, "offset": offset, "total_records": total},
        "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def _haversine_km(a, b):
    lat1, lon1 = map(math.radians, a)
    lat2, lon2 = map(math.radians, b)
    dlat, dlon = lat2 - lat1, lon2 - lon1
    h = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2) ** 2
    return 6371.0088 * 2 * math.asin(math.sqrt(h))


async def _geocode_origin(location, state):
    query = f"{location}, {state}, India"
    async with httpx.AsyncClient(timeout=httpx.Timeout(12), headers={"User-Agent": "KrishiSahyog/1.0"}) as client:
        response = await client.get("https://photon.komoot.io/api/", params={"q": query, "limit": 5, "lang": "en"})
        response.raise_for_status()
        features = response.json().get("features", [])
    for feature in features:
        props = feature.get("properties") or {}
        country = str(props.get("country") or "").strip().lower()
        coords = (feature.get("geometry") or {}).get("coordinates")
        if country and country not in {"india", "in"}:
            continue
        if coords and len(coords) >= 2:
            return float(coords[1]), float(coords[0])
    raise ValueError(f"Could not locate {location}, {state}. Check the location spelling and internet connection.")


async def get_nearest_mandi_candidates(location: str, state: str, district: str = "", limit: int = 3):
    if not location.strip() or not state.strip():
        raise ValueError("Farm location and state are required.")
    origin = await _geocode_origin(location, state)
    with _connect() as con:
        rows = con.execute(
            """SELECT state_name,district_name,market_center_name,
                      market_center_code,latitude,longitude
               FROM mandi_prices
               WHERE state_name=? AND latitude IS NOT NULL AND longitude IS NOT NULL
               GROUP BY state_name,district_name,market_center_name,market_center_code,latitude,longitude""",
            (state,)
        ).fetchall()
    if not rows:
        raise ValueError(f"No market coordinates are available in the local dataset for {state}.")
    located = []
    for row in rows:
        point = (row["latitude"], row["longitude"])
        located.append({
            "market": row["market_center_name"],
            "market_id": str(row["market_center_code"] or ""),
            "state": row["state_name"],
            "state_id": row["state_name"],
            "district": row["district_name"],
            "distance_km": round(_haversine_km(origin, point), 2),
            "latitude": row["latitude"],
            "longitude": row["longitude"],
        })
    located.sort(key=lambda x: x["distance_km"])
    nearest = located[:max(1, min(int(limit), 3))]
    return {
        "source": "Local Agriculture Marketing dataset market coordinates + OpenStreetMap Photon",
        "search_scope": "all_markets_in_selected_state",
        "origin": {"query": location, "state": state, "district_hint": district or None,
                   "latitude": origin[0], "longitude": origin[1]},
        "distance_type": "straight_line_estimate",
        "markets_considered": len(rows),
        "markets_geocoded": len(rows),
        "nearest_markets": nearest,
        "district_expansion_used": any(x["district"].casefold() != district.casefold() for x in nearest) if district else None,
        "note": "Distances are straight-line estimates from market coordinates, not road distances. Verify road distance and transport charges before dispatch.",
    }
