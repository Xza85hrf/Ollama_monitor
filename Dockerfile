FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

ENV OLLAMA_API_BASE=http://127.0.0.1:11435
ENV DEFAULT_TIMEOUT=10
ENV RETRY_ATTEMPTS=3
ENV RETRY_DELAY=2

CMD ["python", "ollama_monitor.py", "--config", "./config.yaml", "--prometheus", "--continuous"]
