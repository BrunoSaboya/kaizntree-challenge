#!/bin/sh
set -e

echo "Waiting for PostgreSQL..."
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
  sleep 1
done

echo "Running migrations..."
python manage.py migrate --noinput

echo "Starting server..."
exec "$@"
