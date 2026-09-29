# syntax=docker/dockerfile:1
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
RUN adduser --disabled-password --gecos "" app && mkdir -p /srv/evals/reports && chown -R app /srv
USER app
EXPOSE 8000
# ONE worker, deliberately. The bus that streams agent progress is a module-level dict
# in this process (`app/core/taskbus.py`: "Single-instance by design"), so with two
# workers a `GET /internal/stream/{taskId}` served by the worker that did *not* start the
# task answers 404 -- and the copilot stream fails roughly half the time, intermittently
# and only in this image. The documented scale-out path is a Redis backplane; until that
# exists, extra workers break streaming rather than scale it.
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--workers","1"]
