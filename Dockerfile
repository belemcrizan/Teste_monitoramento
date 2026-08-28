FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VERTICE_ARTIFACT_DIR=/app/artifacts

WORKDIR /app

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN python -m pip install --no-cache-dir ".[aws]" \
    && useradd --create-home --uid 10001 vertice \
    && mkdir -p /app/artifacts \
    && chown -R vertice:vertice /app

USER 10001
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" || exit 1

CMD ["uvicorn", "vertice_surveillance.bootstrap:app", "--host", "0.0.0.0", "--port", "8000"]

