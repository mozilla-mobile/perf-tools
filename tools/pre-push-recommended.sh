#!/bin/bash

set -e

# We should execute in the virtualenv to ensure we're
# all using the same version of the linter.
if [[ -z "${VIRTUAL_ENV}" ]]; then
    >&2 echo "ERROR: activate the virtualenv before executing the recommended pre-push hook."
    exit 1
fi

pycodestyle
