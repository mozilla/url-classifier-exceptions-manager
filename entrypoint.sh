#!/bin/bash

set -e

get_env_var() {
    local var_name="$1"
    local value="${!var_name}"

    if [ -z "$value" ]; then
        echo "Error: environment variable '$var_name' not set" >&2
        return 1
    else
        echo "$value"
    fi
}

# The environment should be either "stage" or "prod" to indicate the server to
# use.
ENVIRONMENT=$(get_env_var "ENVIRONMENT")

# The authorization token to use for connecting to the Remote Settings server.
AUTHORIZATION=$(get_env_var "AUTHORIZATION")

# Whether to run the command in dry-run mode.
DRY_RUN="${DRY_RUN:-}"

# Check for Bugzilla API key. We need the API key to interact with Bugzilla
# bugs.
BZ_API_KEY=$(get_env_var "BZ_API_KEY")

# Execute the command
uce-manager auto --server "$ENVIRONMENT" --server-location "$SERVER" --auth "$AUTHORIZATION" ${DRY_RUN:+--dry-run} ${FORCE:+--force}
