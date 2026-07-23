FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv/app

RUN addgroup --system jobhunter && adduser --system --ingroup jobhunter jobhunter

COPY pyproject.toml README.md LICENSE ./
COPY app ./app
COPY alembic.ini ./
COPY migrations ./migrations
RUN python -m pip install --upgrade pip && python -m pip install .

COPY config ./config
COPY docker/entrypoint.sh /usr/local/bin/job-hunter-entrypoint
RUN chmod 755 /usr/local/bin/job-hunter-entrypoint && mkdir -p data && chown -R jobhunter:jobhunter /srv/app

USER jobhunter

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8000/api/v1/health', timeout=3).read()"

ENTRYPOINT ["job-hunter-entrypoint"]
