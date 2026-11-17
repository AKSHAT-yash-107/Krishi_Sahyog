import calendar
from datetime import date, datetime, timedelta, timezone
from typing import Optional

import ee

PROJECT_ID = "hal-project-513715"
COLLECTION = "COPERNICUS/S2_SR_HARMONIZED"


def initialize_earth_engine():
    """Initialize Earth Engine with the authenticated local account."""
    try:
        ee.Initialize(project=PROJECT_ID)
    except Exception as exc:
        raise RuntimeError(f"Earth Engine initialization failed: {exc}") from exc



def _normalize_geojson_geometry(geojson):
    """Accept Polygon, MultiPolygon, Feature, or a single-feature FeatureCollection."""

    if not isinstance(geojson, dict):
        raise ValueError("Field boundary must be a GeoJSON object.")

    geojson_type = geojson.get("type")

    if geojson_type == "FeatureCollection":
        features = geojson.get("features")

        if not isinstance(features, list) or len(features) != 1:
            raise ValueError(
                "FeatureCollection must contain exactly one feature."
            )

        feature = features[0]

        if not isinstance(feature, dict) or feature.get("type") != "Feature":
            raise ValueError("Invalid Feature inside FeatureCollection.")

        geojson = feature

    if geojson.get("type") == "Feature":
        geojson = geojson.get("geometry")

    if not isinstance(geojson, dict):
        raise ValueError("GeoJSON geometry is missing or invalid.")

    if geojson.get("type") not in ("Polygon", "MultiPolygon"):
        raise ValueError(
            "Field boundary must contain a Polygon or MultiPolygon geometry."
        )

    return geojson


def _make_region(latitude, longitude, radius_m, polygon_geojson=None):
    if polygon_geojson:
        polygon_geojson = _normalize_geojson_geometry(polygon_geojson)

        try:
            region = ee.Geometry(polygon_geojson)
            region.area(maxError=1).getInfo()
            return region, "polygon"
        except Exception as exc:
            raise ValueError(
                f"Invalid field boundary GeoJSON: {exc}"
            ) from exc

    if latitude is None or longitude is None:
        raise ValueError(
            "Latitude and longitude are required when no polygon is supplied."
        )

    if not -90 <= latitude <= 90:
        raise ValueError("Latitude must be between -90 and 90.")

    if not -180 <= longitude <= 180:
        raise ValueError("Longitude must be between -180 and 180.")

    if not 100 <= radius_m <= 5000:
        raise ValueError("Radius must be between 100 and 5000 metres.")

    return ee.Geometry.Point([longitude, latitude]).buffer(radius_m), "circle"



def _prepare_image(image):
    """Mask cloud/shadow classes and add NDVI/EVI bands."""
    scl = image.select("SCL")
    valid = (
        scl.neq(0)
        .And(scl.neq(1))
        .And(scl.neq(3))
        .And(scl.neq(8))
        .And(scl.neq(9))
        .And(scl.neq(10))
        .And(scl.neq(11))
    )

    reflectance = image.select(["B2", "B4", "B8"]).multiply(0.0001).updateMask(valid)
    blue = reflectance.select("B2")
    red = reflectance.select("B4")
    nir = reflectance.select("B8")

    ndvi = nir.subtract(red).divide(nir.add(red)).rename("NDVI")
    evi = (
        nir.subtract(red)
        .multiply(2.5)
        .divide(nir.add(red.multiply(6)).subtract(blue.multiply(7.5)).add(1))
        .rename("EVI")
    )
    return reflectance.addBands([ndvi, evi]).copyProperties(image, ["system:time_start"])


def _mean_indices(image, region):
    values = image.select(["NDVI", "EVI"]).reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=region,
        scale=10,
        maxPixels=1_000_000_000,
        bestEffort=True,
    ).getInfo()
    return values.get("NDVI"), values.get("EVI")


def _monthly_series(processed, region, start, end):
    """Return monthly median-composite means, skipping months without usable imagery."""
    rows = []
    cursor = date(start.year, start.month, 1)
    month_count = (end.year - start.year) * 12 + end.month - start.month + 1
    if month_count > 24:
        raise ValueError("Choose a date range of 24 months or less for the time series.")

    while cursor <= end:
        if cursor.month == 12:
            next_month = date(cursor.year + 1, 1, 1)
        else:
            next_month = date(cursor.year, cursor.month + 1, 1)

        month_start = max(cursor, start)
        month_end = min(next_month, end + timedelta(days=1))
        month_collection = processed.filterDate(month_start.isoformat(), month_end.isoformat())
        count = month_collection.size().getInfo()

        if count:
            monthly_image = month_collection.median().clip(region)
            ndvi, evi = _mean_indices(monthly_image, region)
            if ndvi is not None and evi is not None:
                rows.append({
                    "month": cursor.strftime("%Y-%m"),
                    "image_count": count,
                    "ndvi_mean": round(float(ndvi), 4),
                    "evi_mean": round(float(evi), 4),
                })
        cursor = next_month
    return rows


def analyze_satellite(
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_m: int = 500,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    max_cloud: float = 30,
    polygon_geojson: Optional[dict] = None,
    crop: Optional[str] = None,
    growth_stage: Optional[str] = None,
):
    """Analyse Sentinel-2 SR imagery for a circular buffer or a supplied GeoJSON field polygon."""
    if not 0 <= max_cloud <= 100:
        raise ValueError("Maximum cloud percentage must be between 0 and 100.")

    today = datetime.now(timezone.utc).date()
    end = date.fromisoformat(end_date) if end_date else today
    start = date.fromisoformat(start_date) if start_date else end - timedelta(days=60)
    if start >= end:
        raise ValueError("Start date must be earlier than end date.")
    if (end - start).days > 730:
        raise ValueError("Date range cannot exceed 24 months.")

    initialize_earth_engine()
    if polygon_geojson:
     polygon_geojson = _normalize_geojson_geometry(polygon_geojson)

    region, area_mode = _make_region(
    latitude,
    longitude,
    radius_m,
    polygon_geojson
)

    collection = (
        ee.ImageCollection(COLLECTION)
        .filterBounds(region)
        .filterDate(start.isoformat(), (end + timedelta(days=1)).isoformat())
        .filter(ee.Filter.lte("CLOUDY_PIXEL_PERCENTAGE", max_cloud))
    )
    image_count = collection.size().getInfo()
    if image_count == 0:
        raise ValueError("No Sentinel-2 images found. Try a wider date range or a higher cloud threshold.")

    processed = collection.map(_prepare_image)
    composite = processed.median().clip(region)
    ndvi_mean, evi_mean = _mean_indices(composite, region)
    if ndvi_mean is None or evi_mean is None:
        raise ValueError("No valid vegetation pixels found. Try another date range or area.")

    latest_image = collection.sort("system:time_start", False).first()
    latest_date = ee.Date(latest_image.get("system:time_start")).format("YYYY-MM-dd").getInfo()

    preview_region = region.bounds(maxError=1)
    ndvi_preview = composite.select("NDVI").getThumbURL({
        "region": preview_region,
        "dimensions": 512,
        "min": -1,
        "max": 1,
        "palette": ["8c510a", "d8b365", "f6e8c3", "c7eae5", "5ab4ac", "01665e"],
    })
    evi_preview = composite.select("EVI").getThumbURL({
        "region": preview_region,
        "dimensions": 512,
        "min": -1,
        "max": 1,
        "palette": ["8c510a", "d8b365", "f6e8c3", "c7eae5", "5ab4ac", "01665e"],
    })

    timeseries = _monthly_series(processed, region, start, end)
    context = {
        "crop": crop,
        "growth_stage": growth_stage,
        "note": (
            "Use the monthly trend to compare this same field over time. A single mean index "
            "cannot diagnose crop stress; interpretation also depends on crop, growth stage, "
            "field boundary, soil background and recent management."
        ),
    }

    area = {"mode": area_mode}
    if area_mode == "circle":
        area.update({"latitude": latitude, "longitude": longitude, "radius_m": radius_m})
    else:
        area["geometry_type"] = polygon_geojson.get("type")

    return {
        "source": "Sentinel-2 SR Harmonized",
        "collection": COLLECTION,
        "area": area,
        "date_range": {"start": start.isoformat(), "end": end.isoformat()},
        "image_count": image_count,
        "latest_image_date": latest_date,
        "indices": {"ndvi_mean": round(float(ndvi_mean), 4), "evi_mean": round(float(evi_mean), 4)},
        "timeseries": timeseries,
        "crop_context": context,
        "previews": {"ndvi": ndvi_preview, "evi": evi_preview},
    }
