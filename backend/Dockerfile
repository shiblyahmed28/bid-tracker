FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    libcairo2 \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Fail the build here, not at PDF-export time in production, if a WeasyPrint
# system dependency (libpango/libcairo/libgdk-pixbuf) is missing.
RUN python -c "from weasyprint import HTML; HTML(string='<h1>build check</h1>').write_pdf('/tmp/weasyprint-build-check.pdf')" \
    && rm /tmp/weasyprint-build-check.pdf

COPY . .

# Match the host dev user's uid/gid (1000) so the bind-mounted source stays
# writable, and don't run the app process as root.
RUN groupadd -g 1000 appuser && useradd -m -u 1000 -g appuser appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
