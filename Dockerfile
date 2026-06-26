FROM python:3.12-slim

WORKDIR /app

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential && \
    rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency resolution
RUN pip install uv

# Copy project files
COPY pyproject.toml .
COPY edith_x/ edith_x/

# Install dependencies
RUN uv pip install --system -e ".[dev]"

# Expose ports
EXPOSE 8000 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s \
    CMD curl -f http://localhost:8000/edith/v1/health || exit 1

CMD ["uvicorn", "edith_x.interfaces.rest.app:app", "--host", "0.0.0.0", "--port", "8000"]
