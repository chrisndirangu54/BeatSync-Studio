FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg libgl1 libglib2.0-0 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt /app/requirements.txt
COPY apps/api/requirements.txt /app/apps/api/requirements.txt
RUN pip install --no-cache-dir -r /app/apps/api/requirements.txt

COPY beatstudio /app/beatstudio
COPY apps/api /app/apps/api

ENV PYTHONPATH=/app
EXPOSE 8080

CMD ["uvicorn","apps.api.main:app","--host","0.0.0.0","--port","8080"]
