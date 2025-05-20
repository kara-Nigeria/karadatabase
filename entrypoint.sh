#!/bin/sh
set -e

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL to be ready..."
until pg_isready -h "${DB_HOST}" -p "${DB_PORT}" -U "${DB_USER}"
do
  echo "Waiting for PostgreSQL..."
  sleep 1
done
echo "PostgreSQL is ready!"

# Execute the command passed to the entrypoint (default: start the migrator)
exec "$@"
