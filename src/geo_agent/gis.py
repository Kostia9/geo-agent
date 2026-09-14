"""Core GIS operations. Every function takes and returns GeoJSON (EPSG:4326)."""

import json

import geopandas as gpd

GeoJSON = dict


def _to_gdf(geojson: GeoJSON) -> gpd.GeoDataFrame:
    features = geojson["features"] if geojson.get("type") == "FeatureCollection" else [geojson]
    return gpd.GeoDataFrame.from_features(features, crs="EPSG:4326")


def _to_geojson(gdf: gpd.GeoDataFrame) -> GeoJSON:
    return json.loads(gdf.to_json())


def buffer(geojson: GeoJSON, distance_m: float) -> GeoJSON:
    gdf = _to_gdf(geojson)
    # Buffering needs a metric CRS, so detour through the local UTM zone.
    projected = gdf.to_crs(gdf.estimate_utm_crs())
    projected["geometry"] = projected.geometry.buffer(distance_m)
    return _to_geojson(projected.to_crs("EPSG:4326"))


def area_m2(geojson: GeoJSON) -> list[float]:
    gdf = _to_gdf(geojson)
    return gdf.to_crs(gdf.estimate_utm_crs()).area.tolist()


def length_m(geojson: GeoJSON) -> list[float]:
    gdf = _to_gdf(geojson)
    return gdf.to_crs(gdf.estimate_utm_crs()).length.tolist()


def centroid(geojson: GeoJSON) -> GeoJSON:
    gdf = _to_gdf(geojson)
    gdf["geometry"] = gdf.geometry.centroid
    return _to_geojson(gdf)


def reproject(geojson: GeoJSON, epsg: int) -> GeoJSON:
    return _to_geojson(_to_gdf(geojson).to_crs(epsg=epsg))


def intersect(left: GeoJSON, right: GeoJSON) -> GeoJSON:
    return _to_geojson(gpd.overlay(_to_gdf(left), _to_gdf(right), how="intersection"))
