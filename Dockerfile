FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir fastapi uvicorn[standard] yt-dlp openai==0.28.0

WORKDIR /app
COPY app.py /app/app.py

ENV OPENAI_API_KEY=""
ENV PORT=8080

EXPOSE 8080
CMD ["uvicorn", "app:api", "--host", "0.0.0.0", "--port", "8080"]
