#!/bin/bash

src/manage.py generate_envvar_docs \
    --file docs/installation/config.rst \
    --exclude-group "Content Security Policy" \
    --exclude-group "Cross-Origin-Resource-Sharing" \
    --exclude-group "Celery" \
    --exclude-group "Logging"
