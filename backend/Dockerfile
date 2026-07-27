FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg nodejs npm && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY pyproject.toml README.md ./
COPY elizato_dl ./elizato_dl
COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt .
COPY backend/app ./app
ENV DATA_DIR=/data PYTHONUNBUFFERED=1
VOLUME ["/data"]
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000"]
