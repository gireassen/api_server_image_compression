FROM python:3.11-alpine

RUN apk add --no-cache \
    postgresql-dev \
    gcc \
    musl-dev \
    zlib-dev \
    jpeg-dev \
    libjpeg-turbo-dev \
    libpq

WORKDIR /tmp
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

FROM python:3.11-alpine
WORKDIR /app

COPY --from=0 /root/.local /root/.local
COPY api_server.py db.py ./

RUN mkdir -p /app/uploads && \
    chmod 777 /app/uploads && \
    find /root/.local -type d -exec chmod 755 {} \;

ENV PATH=/root/.local/bin:$PATH \
    PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000
CMD ["uvicorn", "api_server:app", "--host", "0.0.0.0", "--port", "8000"]