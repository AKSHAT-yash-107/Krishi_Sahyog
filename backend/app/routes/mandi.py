from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.services.mandi_service import get_mandi_prices, get_mandi_filter_options, get_nearest_mandi_candidates

router = APIRouter(prefix="/api/mandi", tags=["Mandi"])


class SellingStrategyRequest(BaseModel):
    state: str = "Madhya Pradesh"
    district: str = "Sagar"
    commodity: str = "Soyabean"
    variety: str = ""
    quantity_quintals: float = Field(gt=0, le=100000)
    transport_rate_per_quintal_km: float = Field(default=0, ge=0, le=100000)
    handling_cost_per_quintal: float = Field(default=0, ge=0, le=100000)
    # Exact AGMARKNET market names mapped to one-way distance in km.
    market_distances_km: dict[str, float] = Field(default_factory=dict)
    markets: list[str] = Field(default_factory=list, min_length=1, max_length=3)


@router.get("/filters")
async def mandi_filters():
    """Dropdown options sourced from the locally imported Agriculture Marketing dataset."""
    try:
        return await get_mandi_filter_options()
    except Exception as exc:
        print(f"MANDI FILTER ERROR: {repr(exc)}")
        raise HTTPException(status_code=502, detail="Could not load local mandi filters. Check that the dataset has been imported.")


@router.get("/nearest")
async def nearest_mandis(
    location: str = Query(..., min_length=2),
    state: str = Query(..., min_length=2),
    district: str = Query(default=""),
):
    """Return the three closest mandis within the selected state, expanding beyond the selected district as needed."""
    try:
        return await get_nearest_mandi_candidates(location, state, district, limit=3)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        print(f"NEAREST MANDI ERROR: {repr(exc)}")
        raise HTTPException(status_code=502, detail="Could not find nearby mandis. Please retry.")


@router.get("/prices")
async def mandi_prices(
    state: str = Query(default="Madhya Pradesh", min_length=1),
    district: str = Query(default="Sagar"),
    commodity: str = Query(default="Wheat", min_length=1),
    market: str = Query(default=""),
    variety: str = Query(default=""),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    try:
        return await get_mandi_prices(
            state=state, district=district, commodity=commodity,
            market=market, variety=variety, limit=limit, offset=offset,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        print(f"MANDI API ERROR: {repr(exc)}")
        raise HTTPException(status_code=502, detail="Local mandi price retrieval failed. Check the imported database.")


@router.post("/selling-strategy")
async def selling_strategy(data: SellingStrategyRequest):
    try:
        for market_name, distance in data.market_distances_km.items():
            if not market_name.strip() or distance < 0:
                raise HTTPException(
                    status_code=422,
                    detail="Market names must be non-empty and distances cannot be negative.",
                )

        if not data.markets:
            raise ValueError("Select the three nearest mandis before comparing prices.")
        # Fetch prices only for the three selected nearby markets.
        import asyncio
        market_payloads = await asyncio.gather(*[
            get_mandi_prices(
                state=data.state, district="", market=market_name,
                commodity=data.commodity, variety=data.variety, limit=100, offset=0,
            ) for market_name in data.markets
        ])
        records = [row for payload in market_payloads for row in payload.get("records", [])]
        mandi_data = {
            "filters": {"state": data.state, "district": data.district or None, "commodity": data.commodity},
            "markets_requested": len(data.markets),
            "latest_arrival_date": max((p.get("latest_arrival_date") for p in market_payloads if p.get("latest_arrival_date")), default=None),
            "data_age_days": min((p.get("data_age_days") for p in market_payloads if p.get("data_age_days") is not None), default=None),
            "data_freshness": ("recent" if min((p.get("data_age_days") for p in market_payloads if p.get("data_age_days") is not None), default=999) <= 2 else "delayed" if min((p.get("data_age_days") for p in market_payloads if p.get("data_age_days") is not None), default=999) <= 7 else "stale"),
        }
        records = [
            row for row in records
            if row.get("reported") is True
            and isinstance(row.get("modal_price"), (int, float))
            and row["modal_price"] > 0
            and row.get("date")
        ]

        if not records:
            return {
                "status": "no_price_data",
                "message": "The local dataset has no reported prices for this selection.",
                "source": "Agriculture Marketing dataset (local CSV)",
                "filters": mandi_data.get("filters"),
                "markets_checked": mandi_data.get("markets_requested", 0),
                "data_freshness": mandi_data.get("data_freshness"),
                "gross_price_ranking": [],
                "net_realization_ranking": [],
            }

        by_market: dict[str, list[dict[str, Any]]] = {}
        for row in records:
            by_market.setdefault(row["market"], []).append(row)

        comparisons = []
        for market_name, market_rows in by_market.items():
            latest_date = max(row["date"] for row in market_rows)
            latest_rows = [row for row in market_rows if row["date"] == latest_date]
            # If variety is specified, service filtering ensures like-for-like.
            # Otherwise show the highest reported variety and flag the comparison.
            chosen = max(latest_rows, key=lambda row: row["modal_price"])
            distance = data.market_distances_km.get(market_name)
            transport = (
                distance * data.transport_rate_per_quintal_km
                if distance is not None else None
            )
            handling = data.handling_cost_per_quintal if distance is not None else None
            total_cost = transport + handling if distance is not None else None
            net = chosen["modal_price"] - total_cost if total_cost is not None else None

            comparisons.append({
                "market": market_name,
                "market_id": chosen.get("market_id"),
                "variety": chosen.get("variety"),
                "price_date": latest_date,
                "gross_price_per_quintal": round(float(chosen["modal_price"]), 2),
                "distance_km_one_way": distance,
                "transport_cost_per_quintal": round(transport, 2) if transport is not None else None,
                "handling_cost_per_quintal": round(handling, 2) if handling is not None else None,
                "net_price_per_quintal": round(net, 2) if net is not None else None,
                "estimated_net_value": round(net * data.quantity_quintals, 2) if net is not None else None,
                "price_unit": chosen.get("price_unit"),
                "transport_cost_status": "estimated" if distance is not None else "distance_not_provided",
            })

        gross_ranking = sorted(comparisons, key=lambda x: x["gross_price_per_quintal"], reverse=True)
        net_ranking = sorted(
            (x for x in comparisons if x["net_price_per_quintal"] is not None),
            key=lambda x: x["net_price_per_quintal"], reverse=True,
        )

        return {
            "status": "success",
            "source": "Agriculture Marketing dataset (local CSV)",
            "filters": mandi_data.get("filters"),
            "quantity_quintals": data.quantity_quintals,
            "transport_rate_per_quintal_km": data.transport_rate_per_quintal_km,
            "handling_cost_per_quintal": data.handling_cost_per_quintal,
            "markets_checked": len(data.markets),
            "markets_with_reported_prices": len(comparisons),
            "markets_with_distance": len(net_ranking),
            "latest_arrival_date": mandi_data.get("latest_arrival_date"),
            "data_age_days": mandi_data.get("data_age_days"),
            "data_freshness": mandi_data.get("data_freshness"),
            "comparison_basis": (
                "Selected variety across markets."
                if data.variety else
                "Highest reported variety per market; varieties may differ, so compare with caution."
            ),
            "highest_gross_price": gross_ranking[0] if gross_ranking else None,
            "best_estimated_net_market": net_ranking[0] if net_ranking else None,
            "gross_price_ranking": gross_ranking,
            "net_realization_ranking": net_ranking,
            "markets_missing_distance": [x["market"] for x in comparisons if x["distance_km_one_way"] is None],
            "disclaimer": (
                "Net values are estimates based on user-supplied one-way distances and cost assumptions. "
                "They exclude unprovided charges, quality deductions, commissions and loading/unloading costs. "
                "Dataset prices are historical reported observations, not guaranteed sale offers."
            ),
        }
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except Exception as exc:
        print(f"SELLING STRATEGY ERROR: {repr(exc)}")
        raise HTTPException(status_code=502, detail="Selling strategy calculation failed.")
