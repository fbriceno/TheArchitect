FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY confluence_generator/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY confluence_generator/ ./confluence_generator/
COPY api/ ./deepwiki_api/

# Create necessary directories
RUN mkdir -p /app/repos /app/wikicache /app/logs

# Set Python path
ENV PYTHONPATH="/app:/app/confluence_generator:/app/deepwiki_api"

# Create non-root user
RUN useradd --create-home --shell /bin/bash confluence && \
    chown -R confluence:confluence /app
USER confluence

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:8002/health || exit 1

# Expose port
EXPOSE 8002

# Run the application
CMD ["python", "-m", "confluence_generator.main"]