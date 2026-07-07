FROM python:3.13-slim

WORKDIR /app

COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

COPY config.py crawler.py predictor.py notifier.py main.py ./
COPY data/ ./data/

CMD ["python", "main.py"]