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

From inside an n8n workflow, reach the API at `http://geo-api:8000` (Docker service name),
not `localhost`.

## Operations

| Endpoint | Body | Returns |
| --- | --- | --- |
| `POST /buffer` | `geojson`, `distance_m` | buffered GeoJSON |
| `POST /area` | `geojson` | area per feature, m² |
| `POST /length` | `geojson` | length per feature, m |
| `POST /centroid` | `geojson` | centroid GeoJSON |
| `POST /reproject` | `geojson`, `epsg` | reprojected GeoJSON |
| `POST /intersect` | `left`, `right` | intersection GeoJSON |

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
src/geo_agent/api.py   HTTP surface over gis.py
workflows/             exported n8n workflow JSON, mounted at /workflows in n8n
data/                  local datasets (gitignored)
```

Workflows built in the n8n UI live only in its volume until exported — save the JSON into
`workflows/` to get it under version control.
