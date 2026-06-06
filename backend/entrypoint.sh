#!/bin/sh
set -e

# Derive DB connection params for the pg_isready readiness check.
# Priority:
#   1. DATABASE_URL  — injected automatically by Railway's PostgreSQL plugin
#   2. PGHOST/PGPORT/PGUSER — also injected by Railway's plugin (individual vars)
#   3. POSTGRES_HOST/PORT/USER — local Docker Compose convention
if [ -n "$DATABASE_URL" ]; then
  _hostport=$(echo "$DATABASE_URL" | sed -E 's|.*@([^/]+)/.*|\1|')
  DB_HOST=$(echo "$_hostport" | cut -d: -f1)
  DB_PORT=$(echo "$_hostport" | cut -d: -f2)
  DB_USER=$(echo "$DATABASE_URL" | sed -E 's|.*://([^:]+):.*|\1|')
elif [ -n "$PGHOST" ]; then
  DB_HOST="$PGHOST"
  DB_PORT="${PGPORT:-5432}"
  DB_USER="${PGUSER:-postgres}"
else
  DB_HOST="${POSTGRES_HOST:-localhost}"
  DB_PORT="${POSTGRES_PORT:-5432}"
  DB_USER="${POSTGRES_USER:-kaizntree}"
fi

echo "Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT}..."
until pg_isready -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER"; do
  sleep 1
done

echo "Running migrations..."
python manage.py migrate --noinput

if [ -n "$BOOTSTRAP_ADMIN_EMAIL" ] && [ -n "$BOOTSTRAP_ADMIN_USERNAME" ] && [ -n "$BOOTSTRAP_ADMIN_PASSWORD" ]; then
  echo "Bootstrapping admin account..."
  python manage.py create_admin \
    --email="$BOOTSTRAP_ADMIN_EMAIL" \
    --username="$BOOTSTRAP_ADMIN_USERNAME" \
    --password="$BOOTSTRAP_ADMIN_PASSWORD" || true
fi

echo "Starting server..."
exec "$@"
