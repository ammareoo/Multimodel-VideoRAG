FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY worker/requirements.txt ./worker/
RUN pip install --no-cache-dir -r worker/requirements.txt

COPY backend /app/backend
COPY worker /app/worker

WORKDIR /app/worker

ENV DATA_DIR=/app/data
ENV PYTHONPATH=/app/backend

CMD ["python", "pipeline.py"]
