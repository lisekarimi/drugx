FROM python:3.11-slim

# Install uv package manager
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Create non-root user
RUN useradd -m -u 1000 appuser

# Configure environment
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV PATH="/opt/venv/bin:${PATH}"
ENV PYTHONPATH=/app

# Use temp directory for caches (fixes permission issues)
ENV UV_CACHE_DIR=/tmp/uv-cache
ENV HF_HOME=/tmp/.cache
ENV STREAMLIT_CONFIG_DIR=/tmp/.streamlit

# Configure Streamlit for headless operation
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

WORKDIR /app

# Install dependencies
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Copy source code
COPY . .

# Set proper permissions
RUN chown -R appuser:appuser /app /opt/venv

# Switch to non-root user
USER appuser

# Expose Streamlit port
EXPOSE 7860

# Run Streamlit
CMD ["streamlit", "run", "src/frontend/app.py", "--server.address", "0.0.0.0", "--server.port", "7860"]
