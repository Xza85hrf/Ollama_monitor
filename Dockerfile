FROM python:3.12-slim

# Create non-root user
RUN useradd -m -u 1000 monitor && \
    mkdir -p /app && \
    chown monitor:monitor /app

WORKDIR /app

# Copy and install dependencies
COPY --chown=monitor:monitor requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=monitor:monitor . .

# Switch to non-root user
USER monitor

# Add health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000').read()"

EXPOSE 8000

ENV OLLAMA_API_BASE=http://127.0.0.1:11435
ENV DEFAULT_TIMEOUT=10
ENV RETRY_ATTEMPTS=3
ENV RETRY_DELAY=2

CMD ["python", "ollama_monitor.py", "--config", "./config.yaml", "--prometheus", "--continuous"]
