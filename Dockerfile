FROM python:3.11-slim

RUN pip install --no-cache-dir uv
RUN useradd -m -u 1000 appuser

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:${PATH}" \
    PYTHONPATH=/app \
    UV_CACHE_DIR=/tmp/uv-cache \
    HF_HOME=/tmp/.cache \
    STREAMLIT_CONFIG_DIR=/tmp/.streamlit \
    STREAMLIT_SERVER_HEADLESS=true \
    STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

COPY . .

RUN chown -R appuser:appuser /app /opt/venv
USER appuser

EXPOSE 7860

CMD ["streamlit", "run", "src/frontend/app.py", \
     "--server.address=0.0.0.0", "--server.port=7860"]
