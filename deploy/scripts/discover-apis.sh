#!/bin/bash
# Discover all APIs in the apis/ directory
# Structure: apis/exposed/<name>-b4f-api/ and apis/internal/<name>-backend-api/

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

    # Scan exposed/ and internal/ layers
    for layer in exposed internal; do
        local layer_dir="${APIS_DIR}/${layer}"
        [[ -d "${layer_dir}" ]] || continue

        for dir in "${layer_dir}"/*; do
            if [[ -d "${dir}" ]] && [[ -f "${dir}/Dockerfile" ]]; then
                local dir_name
                dir_name=$(basename "${dir}")
                # Skip the shared directory
                if [[ "${dir_name}" == "shared" ]]; then
                    continue
                fi
                apis+=("${dir_name}")
            fi
        done
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
