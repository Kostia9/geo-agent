FROM python:3.12-slim

# rasterio's wheels bundle GDAL but still link against the system libexpat
RUN apt-get update \
    && apt-get install -y --no-install-recommends libexpat1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
COPY src ./src
RUN pip install --no-cache-dir .

EXPOSE 8000
CMD ["uvicorn", "geo_agent.api:app", "--host", "0.0.0.0", "--port", "8000"]
