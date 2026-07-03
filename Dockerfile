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

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create directories
WORKDIR /app
RUN mkdir -p /app/logs /app/storage /app/data

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Expose port (optional, for monitoring)
EXPOSE 8000

# Run the bot (default: paper trading mode)
CMD ["python", "main.py", "paper", "--pairs", "BTC_IDR", "--timeframe", "1h", "--interval", "5"]
