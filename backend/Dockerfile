FROM python:3.12-slim AS base

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── development ─────────────────────────────────────────────────────────────
FROM base AS development

COPY requirements-dev.txt .
RUN pip install --no-cache-dir -r requirements-dev.txt

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY . .

ENTRYPOINT ["/entrypoint.sh"]
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ── production ───────────────────────────────────────────────────────────────
FROM base AS production

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

COPY . .

RUN DJANGO_SETTINGS_MODULE=kaizntree.settings.production \
    DJANGO_SECRET_KEY=dummy \
    POSTGRES_DB=dummy POSTGRES_USER=dummy POSTGRES_PASSWORD=dummy POSTGRES_HOST=dummy \
    python manage.py collectstatic --noinput

# Persist the settings module so both manage.py (entrypoint migrations) and
# gunicorn use production settings at runtime — not the development default
# in manage.py.
ENV DJANGO_SETTINGS_MODULE=kaizntree.settings.production

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
# Shell form (not JSON array) so $PORT is expanded at container start.
# Railway injects $PORT; local Docker falls back to 8000.
CMD gunicorn kaizntree.wsgi:application --bind "0.0.0.0:${PORT:-8000}" --workers 3
