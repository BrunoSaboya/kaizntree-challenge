#!/bin/sh
set -e

# On Railway, DATABASE_URL is injected by the PostgreSQL plugin.
# On local Docker Compose, POSTGRES_* vars are set instead.
# Derive the connection params for the pg_isready check from whichever is present.
if [ -n "$DATABASE_URL" ]; then
  # Extract host:port from postgresql://user:pass@host:port/dbname
  _hostport=$(echo "$DATABASE_URL" | sed -E 's|.*@([^/]+)/.*|\1|')
  DB_HOST=$(echo "$_hostport" | cut -d: -f1)
  DB_PORT=$(echo "$_hostport" | cut -d: -f2)
  DB_USER=$(echo "$DATABASE_URL" | sed -E 's|.*://([^:]+):.*|\1|')
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

echo "Starting server..."
exec "$@"
