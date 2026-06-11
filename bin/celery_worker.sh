#!/bin/bash

set -e

LOGLEVEL=${CELERY_LOGLEVEL:-INFO}
CONCURRENCY=${CELERY_WORKER_CONCURRENCY:-1}

# Celery reads CELERY_WORKER_* environment variables natively (Click
# auto_envvar_prefix="CELERY"), so any worker option can be overridden from the
# environment. Default to recycling pool children periodically so memory
# released by completed tasks is returned to the OS instead of accumulating in
# a long-lived child process. Recycling happens between tasks; no work is lost.
# CELERY_WORKER_MAX_MEMORY_PER_CHILD (in KiB) can be set as a companion limit.
export CELERY_WORKER_MAX_TASKS_PER_CHILD=${CELERY_WORKER_MAX_TASKS_PER_CHILD:-50}

QUEUE=${CELERY_WORKER_QUEUE:=celery}
WORKER_NAME=${CELERY_WORKER_NAME:="${QUEUE}"@%n}

_binary=$(which celery)

if [[ "$ENABLE_COVERAGE" ]]; then
    _binary="coverage run $_binary"
fi

echo "Starting celery worker $WORKER_NAME with queue $QUEUE"
exec $_binary --workdir src --app woo_publications.celery worker \
    -Q $QUEUE \
    -n $WORKER_NAME \
    -l $LOGLEVEL \
    -O fair \
    -c $CONCURRENCY
