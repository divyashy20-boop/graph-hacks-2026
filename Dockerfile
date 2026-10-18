FROM python:3.12-slim
WORKDIR /app
COPY pyproject.toml ./
COPY ugi ./ugi
COPY demo ./demo
COPY benchmarks ./benchmarks
RUN pip install --no-cache-dir . && useradd --create-home appuser && mkdir -p /var/lib/ugi && chown appuser:appuser /var/lib/ugi
USER appuser
EXPOSE 8000
CMD ["uvicorn", "ugi.api:app", "--host", "0.0.0.0", "--port", "8000"]
