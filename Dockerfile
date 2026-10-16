# Shot Director in demo mode: no keys, no GPU, no network needed at runtime.
#   docker build -t shot-director .
#   docker run --rm -p 8000:8000 shot-director        # then open http://127.0.0.1:8000
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
RUN useradd --create-home --uid 10001 app && mkdir -p /app/outputs && chown -R app /app/outputs
USER app

# DEMO=1 disables every engine that could spend credits. Do not put keys in the image.
ENV DEMO=1 HOST=0.0.0.0 PORT=8000 PYTHONUNBUFFERED=1
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "import urllib.request;urllib.request.urlopen('http://127.0.0.1:8000/api/config',timeout=3)" || exit 1
CMD ["python", "-m", "app.server"]
