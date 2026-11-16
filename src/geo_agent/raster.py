"""Raster operations that need pixel locations (TiTiler only returns aggregate numbers)."""

from typing import Literal

import numpy as np
import rasterio
from pyproj import Transformer
from rasterio.mask import mask
from rasterio.transform import xy

from geo_agent.gis import GeoJSON, _to_gdf

# Real data is in [0, 1]; the rasters' nodata values are huge negative floats
# (-3.4e38 / -3.4e39) that do not always round-trip exactly, so filter by range too.
_NODATA_FLOOR = -1e30


def _as_feature_geojson(geojson: GeoJSON) -> GeoJSON:
    if geojson.get("type") in {"Feature", "FeatureCollection"}:
        return geojson
    return {"type": "Feature", "properties": {}, "geometry": geojson}


def extremum(
    path: str,
    geojson: GeoJSON,
    mode: Literal["max", "min"] = "max",
    max_points: int = 5,
    ignore_zero: bool = False,
) -> GeoJSON:
    """Find where the raster reaches its max/min inside the polygon(s).

    Returns a FeatureCollection of pixel-centre points (EPSG:4326). Raster values are often
    repeated, so every pixel sharing the extreme value counts as a tie; up to `max_points`
    of them are returned, spread evenly over the ties. Summary fields sit next to `features`.
    `ignore_zero` skips 0 ("unsuitable" land), which otherwise dominates every minimum.
    """
    gdf = _to_gdf(_as_feature_geojson(geojson))
    gdf = gdf[gdf.geometry.notna() & gdf.geom_type.isin(["Polygon", "MultiPolygon"])]
    if gdf.empty:
        raise ValueError("A Polygon or MultiPolygon is required to search for an extremum.")

    with rasterio.open(path) as src:
        shapes = list(gdf.to_crs(src.crs).geometry)
        band = transform = None
        # A polygon smaller than a pixel may cover no pixel centre: retry with all_touched.
        for all_touched in (False, True):
            try:
                data, transform = mask(src, shapes, crop=True, filled=False, all_touched=all_touched)
            except ValueError as exc:  # rasterio: "Input shapes do not overlap raster."
                raise ValueError("The polygon does not overlap the raster.") from exc
            band = data[0]
            values = np.ma.getdata(band)
            valid = ~np.ma.getmaskarray(band) & np.isfinite(values) & (values > _NODATA_FLOOR)
            if ignore_zero:
                valid &= values != 0
            if valid.any():
                break
        if not valid.any():
            raise ValueError(
                "The polygon contains no non-zero raster pixels." if ignore_zero
                else "The polygon contains no valid raster pixels."
            )

        target = values[valid].max() if mode == "max" else values[valid].min()
        rows, cols = np.nonzero(valid & (values == target))
        ties = len(rows)
        pick = np.unique(np.linspace(0, ties - 1, num=min(max_points, ties)).round().astype(int))
        xs, ys = xy(transform, rows[pick], cols[pick])  # pixel centres, raster CRS
        lons, lats = Transformer.from_crs(src.crs, "EPSG:4326", always_xy=True).transform(xs, ys)
        pixel_size_m = abs(src.res[0])

    features = [
        {
            "type": "Feature",
            "properties": {"mode": mode, "value": float(target), "rank": i + 1},
            "geometry": {"type": "Point", "coordinates": [round(lon, 6), round(lat, 6)]},
        }
        for i, (lon, lat) in enumerate(zip(np.atleast_1d(lons), np.atleast_1d(lats)))
    ]
    return {
        "type": "FeatureCollection",
        "features": features,
        "mode": mode,
        "ignore_zero": ignore_zero,
        "value": float(target),
        "tied_pixels": int(ties),
        "points_returned": len(features),
        "valid_pixels": int(valid.sum()),
        "pixel_size_m": pixel_size_m,
    }
