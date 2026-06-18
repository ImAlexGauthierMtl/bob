#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APIS_DIR="$SCRIPT_DIR/apis"
REPORT_DIR="$SCRIPT_DIR/test-reports"
COVERAGE_DIR="$SCRIPT_DIR/coverage-reports"
filter="${1:-}"

mkdir -p "$REPORT_DIR" "$COVERAGE_DIR"
export PYTHONPATH="$APIS_DIR:${PYTHONPATH:-}"

pass=0
fail=0
skip=0

for layer in exposed internal; do
  [ -d "$APIS_DIR/$layer" ] || continue
  for api_dir in "$APIS_DIR/$layer"/*-api/; do
    [ -d "$api_dir" ] || continue
    api_name="$(basename "$api_dir")"
    if [ -n "$filter" ] && [ "$api_name" != "$filter" ]; then
      continue
    fi

    if [ ! -x "$api_dir/run_tests.sh" ]; then
      printf '[skip] %s/%s missing run_tests.sh\n' "$layer" "$api_name"
      skip=$((skip + 1))
      continue
    fi

    printf '[test] %s/%s\n' "$layer" "$api_name"
    if (cd "$api_dir" && ./run_tests.sh); then
      pass=$((pass + 1))
      [ -f "$api_dir/junit.xml" ] && cp "$api_dir/junit.xml" "$REPORT_DIR/$api_name-junit.xml"
      [ -f "$api_dir/coverage.xml" ] && cp "$api_dir/coverage.xml" "$COVERAGE_DIR/$api_name-coverage.xml"
    else
      fail=$((fail + 1))
    fi
  done
done

printf '[test] passed=%s failed=%s skipped=%s reports=%s coverage=%s\n' "$pass" "$fail" "$skip" "$REPORT_DIR" "$COVERAGE_DIR"
[ "$fail" -eq 0 ]
