#!/bin/bash
#
# Generate the API schema from the code into the output file.
#
# Run this script from the root of the repository:
#
#   ./bin/generate_api_schema.sh [application] [outfile]
#
# 'outfile' defaults to `src/woo_publications/api/[application]_api/openapi.yml`
#
set -e -o pipefail

if [[ -z "$VIRTUAL_ENV" ]] && [[ ! -v GITHUB_ACTIONS ]]; then
    echo "You need to activate your virtual env before running this script"
    exit 1
fi

if [ "$1" = "" ]; then
    echo "You need to pass the API name in the first argument"
    exit 1
fi

case "$1" in
    application|researcher)
        ;;
    *)
        echo "The valid first argument options are 'application' and 'researcher'."
        exit 1
esac

export SCHEMA_PATH=src/woo_publications/api/$1_api

OUTPUT_FILE=$2

echo "Generating OAS schema for $1..."
src/manage.py spectacular_for_api \
    --file ${OUTPUT_FILE:-$SCHEMA_PATH/openapi.yaml} \
    --lang="nl-nl" \
    --validate \
    --component $1_api

echo "Done."
