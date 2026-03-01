# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install uv for faster dependency resolution
RUN pip install --no-cache-dir uv

# Install Python dependencies using uv
RUN uv pip install --system --no-cache -r pyproject.toml

# Install Flask for main.py wrapper
RUN pip install --no-cache-dir flask

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p history schemas

# Expose port (Cloud Run will set PORT env var)
ENV PORT=8080
EXPOSE 8080

# Set environment variables for Streamlit
ENV STREAMLIT_SERVER_PORT=8080
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0
ENV STREAMLIT_SERVER_HEADLESS=true
ENV STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Health check
# Streamlit 本身不保證提供 /health，因此以 / 作為最小存活檢查。
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT}/ || exit 1

# Run the application
CMD ["python", "main.py"]
