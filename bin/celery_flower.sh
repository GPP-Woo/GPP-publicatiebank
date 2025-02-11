#!/bin/bash
exec celery --app woo_publications.celery --workdir src flower
