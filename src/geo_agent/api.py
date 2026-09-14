"""HTTP surface over the GIS operations, called by n8n's HTTP Request node."""

from fastapi import FastAPI
from pydantic import BaseModel, Field

from geo_agent import gis

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
