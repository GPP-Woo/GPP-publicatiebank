#!/bin/bash

set -ex

# Wait for the database container
# See: https://docs.docker.com/compose/startup-order/
export PGHOST=${DB_HOST:-db}
export PGPORT=${DB_PORT:-5432}

fixtures_dir=${FIXTURES_DIR:-/app/fixtures}

uwsgi_port=${UWSGI_PORT:-8000}
uwsgi_processes=${UWSGI_PROCESSES:-4}
uwsgi_threads=${UWSGI_THREADS:-1}

mountpoint=${SUBPATH:-/}

# Figure out abspath of this script
SCRIPT=$(readlink -f "$0")
SCRIPTPATH=$(dirname "$SCRIPT")

until pg_isready; do
  >&2 echo "Waiting for database connection..."
  sleep 1
done

>&2 echo "Database is up."

# Apply database migrations
>&2 echo "Apply database migrations"
python src/manage.py migrate

# Load fixtures distributed in the image
echo "Loading required fixtures"
python src/manage.py loaddata themes
python src/manage.py load_information_categories \
    information_categories
python src/manage.py load_organisations \
    organisations

# Load any JSON fixtures present in the configured fixtures dir
if [ -d $fixtures_dir ]; then
    echo "Loading fixtures from $fixtures_dir"

    for fixture in $(ls "$fixtures_dir/"*.json)
    do
        echo "Loading fixture $fixture"
        python src/manage.py loaddata $fixture
    done
fi

# Create superuser
# specify password by setting DJANGO_SUPERUSER_PASSWORD in the env
# specify username by setting ODRC_SUPERUSER_USERNAME in the env
# specify email by setting ODRC_SUPERUSER_EMAIL in the env
if [ -n "${ODRC_SUPERUSER_USERNAME}" ]; then
    python src/manage.py createinitialsuperuser \
        --no-input \
        --username "${ODRC_SUPERUSER_USERNAME}" \
        --email "${ODRC_SUPERUSER_EMAIL:-admin\@admin.org}"
    unset ODRC_SUPERUSER_USERNAME ODRC_SUPERUSER_EMAIL DJANGO_SUPERUSER_PASSWORD
fi

# Start server
>&2 echo "Starting server"
exec uwsgi \
    --ini "${SCRIPTPATH}/uwsgi.ini" \
    --master \
    --http :$uwsgi_port \
    --http-keepalive \
    --http-timeout=1800 \
    --manage-script-name \
    --mount $mountpoint=woo_publications.wsgi:application \
    --static-map /static=/app/static \
    --static-map /media=/app/media  \
    --chdir src \
    --enable-threads \
    --processes $uwsgi_processes \
    --threads $uwsgi_threads \
    --post-buffering=8192 \
    --buffer-size=65535 \
    --harakiri=1800
    # processes & threads are needed for concurrency without nginx sitting inbetween
