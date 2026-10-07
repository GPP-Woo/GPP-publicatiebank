#!/bin/bash

set -ex

# Wait for the database container
# See: https://docs.docker.com/compose/startup-order/
export PGHOST=${DB_HOST:-db}
export PGPORT=${DB_PORT:-5432}

fixtures_dir=${FIXTURES_DIR:-/app/fixtures}

gunicorn_port=${GUNICORN_PORT:-8000}

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
exec gunicorn \
    --bind :$gunicorn_port \
    --chdir src \
    --threads ${GUNICORN_THREADS:-1} \
    --workers ${GUNICORN_PROCESSES:-4} \
    --keep-alive 5 \
    --timeout ${GUNICORN_HTTP_TIMEOUT:-1800} \
    --limit-request-field_size ${GUNICORN_BUFFER_SIZE:-65535} \
    --access-logfile - \
    --error-logfile - \
    --logger-class woo_publications.gunicorn_files.JsonGunicornLogger \
    woo_publications.wsgi:application
