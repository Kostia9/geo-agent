# geo-agent

Асистент для аналізу геопросторових даних та виконання GIS-операцій.

Two pieces that talk over HTTP:

- **`geo-api`** — a FastAPI service wrapping GeoPandas/Shapely/rasterio. It exposes GIS
  operations as endpoints that take and return GeoJSON.
- **n8n** — orchestrates the agent workflows (LLM nodes, triggers, credentials) and calls
  `geo-api` through the HTTP Request node.

## Quickstart

```bash
docker compose up -d --build
```

- n8n editor: http://localhost:5678
- geo-api docs: http://localhost:8020/docs
- **map + agent chat: http://localhost:8080**
- original KPI geoportal page: http://localhost:8080/maps/SolarWindMaps.html
- TiTiler: http://localhost:8010/docs

From inside an n8n workflow, reach the API at `http://geo-api:8000` (Docker service name),
not `localhost`.

## Map + chat UI (`web/`)

`web/index.html` is a single page: Leaflet map on the left, agent chat on the right.

- Draw polygons, rectangles, lines or points (leaflet.draw toolbar); each object gets a
  letter label (A, B, …). Click an object to select/deselect it. Selected objects are
  appended to the chat message as GeoJSON under a `[Selected geometries]` block, so you can
  ask "площа і середній сонячний потенціал A" or "перетин A і B".
- Click empty map to read solar/wind values at that point; Alt+click reads them *under* an
  object without selecting it.
- The "Об'єкти" panel (top right) lists every object with select / hide / delete. Hidden
  objects leave the map but keep their label, and if selected are still sent to the agent.
- The agent's AI Agent node has `returnIntermediateSteps` on; the page reads the tool calls
  from the response and draws their geometries (buffer, centroid, intersection, raster
  max/min points, found locations, queried points) as new selectable objects, so results
  can be chained. A new geometry-returning tool must be added to `GEOMETRY_TOOLS` in
  `web/index.html` (n8n tool name with underscores) to be drawn.
- nginx (`web/nginx.conf`) serves the page and proxies `/titiler/` and n8n's
  `/webhook/` paths, so the browser only talks to `localhost:8080`.

## Geoportal and rasters

A local [TiTiler](https://developmentseed.org/titiler/) (`titiler` service) serves the solar
and wind rasters to both the Leaflet geoportal and the agent (the raster-value tools in n8n
and `geo-api`'s `/raster/statistics`). The files live in `data/geoportal/` (gitignored), so
fetch them once on a fresh checkout:

```bash
mkdir -p data/geoportal && cd data/geoportal
for f in solar_cog_rgb_32636 solar_cog_original_32636 wind_cog_rgb_32636 wind_cog_original_32636; do
  curl -fO "https://mmda.ipt.kpi.ua/solar_map/$f.tif"
done
```

`SolarWindMaps.html` also goes in `data/geoportal/`, with `TITILER = 'http://localhost:8010/cog'`
and raster paths `file:///data/geoportal/<name>.tif` (the path inside the `titiler` container).
TiTiler 2.x serves COG endpoints under `/cog` (`/cog/point`, `/cog/statistics`, …).
`*_rgb_*` rasters are the rendered colour maps; `*_original_*` hold the suitability values.

## Operations

| Endpoint | Body | Returns |
| --- | --- | --- |
| `POST /buffer` | `geojson`, `distance_m` | buffered GeoJSON |
| `POST /area` | `geojson` | area per feature, m² |
| `POST /length` | `geojson` | length per feature, m |
| `POST /centroid` | `geojson` | centroid GeoJSON |
| `POST /reproject` | `geojson`, `epsg` | reprojected GeoJSON |
| `POST /intersect` | `left`, `right` | intersection GeoJSON |
| `POST /raster/statistics` | `layer` (solar\|wind), `geojson` | zonal stats via TiTiler |
| `POST /raster/extremum` | `layer`, `geojson`, `mode` (max\|min), `ignore_zero`, `max_points` | points (pixel centres) where the layer is max/min inside the polygon, plus `value` and `tied_pixels` |

Input is assumed to be EPSG:4326. Metric operations reproject to the local UTM zone
internally, so distances and areas come back in metres.

## Local development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .
uvicorn geo_agent.api:app --reload
```

## Layout

```
src/geo_agent/gis.py   GIS operations (GeoJSON in, GeoJSON out)
src/geo_agent/api.py   HTTP surface over gis.py / raster.py
src/geo_agent/raster.py  pixel-level raster ops (rasterio), e.g. max/min location
workflows/             exported n8n workflow JSON, mounted at /workflows in n8n
web/                   map + chat UI and its nginx config
data/                  local datasets (gitignored); data/geoportal/ = rasters + map HTML
```

Workflows built in the n8n UI live only in its volume until exported — save the JSON into
`workflows/` to get it under version control.
