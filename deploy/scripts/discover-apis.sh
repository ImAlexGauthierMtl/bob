#!/bin/bash
# Discover all APIs in the apis/ directory
# Croo structure: APIs are directly in apis/ (e.g. apis/auth-api/, apis/crm-backend-api/)
# B4F APIs use ~ in folder name (e.g. apis/auth~b4f-api/) which maps to auth-b4f-api in k8s

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../../" && pwd)"
APIS_DIR="${PROJECT_ROOT}/apis"

discover_apis() {
    local apis=()

    if [[ ! -d "${APIS_DIR}" ]]; then
        echo "Warning: ${APIS_DIR} does not exist" >&2
        return 0
    fi

    for dir in "${APIS_DIR}"/*; do
        if [[ -d "${dir}" ]] && [[ -f "${dir}/Dockerfile" ]]; then
            local dir_name
            dir_name=$(basename "${dir}")
            # Skip the shared directory
            if [[ "${dir_name}" == "shared" ]]; then
                continue
            fi
            # Convert ~ to - for Kubernetes-safe names (auth~b4f-api -> auth-b4f-api)
            local api_name="${dir_name//\~/-}"
            apis+=("${api_name}")
        fi
    done

    if [[ ${#apis[@]} -gt 0 ]]; then
        IFS=$'\n' sorted_apis=($(sort <<<"${apis[*]}"))
        unset IFS
        printf '%s\n' "${sorted_apis[@]}"
    fi
}

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    discover_apis
fi
