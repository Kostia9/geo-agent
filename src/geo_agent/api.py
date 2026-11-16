"""HTTP surface over the GIS operations, called by n8n's HTTP Request node."""

import os

from fastapi import FastAPI
from pydantic import BaseModel, Field
import httpx
from typing import Literal
from fastapi import HTTPException

from rasterio.errors import RasterioIOError

from geo_agent import gis, raster

app = FastAPI(title="geo-agent", version="0.1.0")


class GeoJSONBody(BaseModel):
    geojson: dict


class BufferBody(GeoJSONBody):
    distance_m: float = Field(gt=0)


class ReprojectBody(GeoJSONBody):
    epsg: int


class IntersectBody(BaseModel):
    left: dict
    right: dict

class RasterStatisticsBody(BaseModel):
    geojson: dict
    layer: Literal["solar", "wind"]

# Defaults point at the remote KPI TiTiler; docker-compose overrides them
# to use the local `titiler` service once the rasters are in data/geoportal/.
RASTER_DIR = os.environ.get("RASTER_DIR", "/var/www/mmda.ipt.kpi.ua/solar_map")
RASTERS = {
    "solar": f"file://{RASTER_DIR}/solar_cog_original_32636.tif",
    "wind": f"file://{RASTER_DIR}/wind_cog_original_32636.tif",
}

TITILER_URL = os.environ.get("TITILER_URL", "https://mmda.ipt.kpi.ua/titiler")

# Same rasters read directly by geo-api (./data is mounted at /data) for pixel-level ops.
LOCAL_RASTER_DIR = os.environ.get("LOCAL_RASTER_DIR", "/data/geoportal")
LOCAL_RASTERS = {
    "solar": f"{LOCAL_RASTER_DIR}/solar_cog_original_32636.tif",
    "wind": f"{LOCAL_RASTER_DIR}/wind_cog_original_32636.tif",
}


class RasterExtremumBody(RasterStatisticsBody):
    mode: Literal["max", "min"] = "max"
    max_points: int = Field(default=5, ge=1, le=50)
    ignore_zero: bool = False


@app.post("/raster/extremum")
def raster_extremum(body: RasterExtremumBody) -> dict:
    """Points where the layer reaches its max (or min) inside the polygon."""
    try:
        result = raster.extremum(
            LOCAL_RASTERS[body.layer], body.geojson, body.mode, body.max_points, body.ignore_zero
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RasterioIOError as exc:  # missing or unreadable file
        raise HTTPException(status_code=503, detail=f"Raster for '{body.layer}' is not available") from exc
    return {"layer": body.layer, **result}


@app.post("/raster/statistics")
def raster_statistics(body: RasterStatisticsBody) -> dict:
    geojson = body.geojson

    if geojson.get("type") in {"Polygon", "MultiPolygon"}:
        geojson = {
            "type": "Feature",
            "properties": {},
            "geometry": geojson,
        }

    response = httpx.post(
        f"{TITILER_URL}/statistics",
        params={"url": RASTERS[body.layer]},
        json=geojson,
        timeout=30,
    )

    if response.is_error:
        raise HTTPException(
            status_code=response.status_code,
            detail=response.text,
        )

    return response.json()

    
@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/buffer")
def buffer(body: BufferBody) -> dict:
    return gis.buffer(body.geojson, body.distance_m)


@app.post("/area")
def area(body: GeoJSONBody) -> dict:
    return {"area_m2": gis.area_m2(body.geojson)}


@app.post("/length")
def length(body: GeoJSONBody) -> dict:
    return {"length_m": gis.length_m(body.geojson)}


@app.post("/centroid")
def centroid(body: GeoJSONBody) -> dict:
    return gis.centroid(body.geojson)


@app.post("/reproject")
def reproject(body: ReprojectBody) -> dict:
    return gis.reproject(body.geojson, body.epsg)


@app.post("/intersect")
def intersect(body: IntersectBody) -> dict:
    return gis.intersect(body.left, body.right)
