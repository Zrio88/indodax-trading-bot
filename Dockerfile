# Dockerfile for Indodax Trading Bot
# Multi-stage build for smaller final image

# Stage 1: Builder
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install TA-Lib (requires compilation)
RUN pip install --no-cache-dir ta-lib

# Stage 2: Runtime
FROM python:3.11-slim

RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN groupadd -r bot && useradd -r -g bot -d /app -s /sbin/nologin bot

# Create directories with correct ownership
WORKDIR /app
RUN mkdir -p /app/logs /app/storage /app/data && chown -R bot:bot /app

# Copy application code (use .dockerignore to exclude secrets)
COPY --chown=bot:bot . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER bot

# Healthcheck (checks bot process is alive)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD ps aux | grep -q "python main.py" || exit 1

# Run the bot (default: paper trading mode)
CMD ["python", "main.py", "paper", "--pairs", "BTC_IDR", "--timeframe", "1h", "--interval", "5"]
