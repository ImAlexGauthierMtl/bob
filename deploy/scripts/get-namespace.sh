#!/bin/bash
# Get Kubernetes namespace for environment

set -euo pipefail

ENV="${1:-dev}"

case "${ENV}" in
    dev|development)
        echo "cde-dev"
        ;;
    staging|stage)
        echo "cde-staging"
        ;;
    prod|production)
        echo "cde-prod"
        ;;
    *)
        if [[ "${ENV}" =~ ^review- ]]; then
            echo "cde-${ENV}"
        else
            echo "Unknown environment: ${ENV}" >&2
            echo "Usage: $0 [dev|staging|prod|review-*]" >&2
            exit 1
        fi
        ;;
esac
