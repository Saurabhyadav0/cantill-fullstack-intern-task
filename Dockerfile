# Single service: FastAPI serves the API and the static frontend.
FROM python:3.12-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code (data/ is provided via volume or at deploy time — not in the public repo)
COPY engine/ engine/
COPY api/ api/
COPY web/ web/
COPY docs/ docs/
# If data exists in the build context (local build), include it; harmless if absent.
COPY data/ ./data/

EXPOSE 8000
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
