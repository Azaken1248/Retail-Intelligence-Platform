# ── Build Stage ──────────────────────────────────────────────
FROM python:3.11-slim AS builder

WORKDIR /build

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Runtime Stage ────────────────────────────────────────────
FROM python:3.11-slim

LABEL maintainer="Rohit Sinha"
LABEL description="Retail Intelligence Platform — FastAPI + MCP Server"

# Bring installed packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy application code
COPY . .

# Non-root user for security
RUN addgroup --system appgroup && \
    adduser --system --ingroup appgroup appuser
USER appuser

# FastAPI default port
EXPOSE 8000
# MCP server default port
EXPOSE 8001

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Default: run the FastAPI server
# Override with CMD to run MCP server instead
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
