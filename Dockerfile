FROM python:3.11-slim

RUN useradd --create-home --shell /usr/sbin/nologin auditor

WORKDIR /app
COPY scripts/ ./scripts/
RUN mkdir -p /app/data && chown -R auditor /app

USER auditor

ENV CLAIM_MEMORY_DB=/app/data/memory.db \
    PYTHONUNBUFFERED=1

EXPOSE 8090

HEALTHCHECK --interval=30s --timeout=3s CMD python3 -c "import urllib.request,os;urllib.request.urlopen('http://127.0.0.1:%s/health'%(os.environ.get('CLAIM_AUDITOR_PORT') or os.environ.get('PORT') or '8090'))"

CMD ["python3", "scripts/auditor_server.py"]
