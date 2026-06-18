#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
APIS_DIR="$SCRIPT_DIR/apis"
RUN_DIR="$SCRIPT_DIR/.run"
PID_DIR="$RUN_DIR/api-pids"
LOG_DIR="$RUN_DIR/logs"

usage() {
  printf 'Usage: %s [--stop|--restart] [api-name]\n' "$(basename "$0")"
}

command="start"
filter=""
for arg in "$@"; do
  case "$arg" in
    --stop) command="stop" ;;
    --restart) command="restart" ;;
    -h|--help) usage; exit 0 ;;
    *) filter="$arg" ;;
  esac
done

stop_apis() {
  mkdir -p "$PID_DIR"
  local stopped=0
  for pid_file in "$PID_DIR"/*.pid; do
    [ -e "$pid_file" ] || continue
    local api_name pid
    api_name="$(basename "$pid_file" .pid)"
    if [ -n "$filter" ] && [ "$api_name" != "$filter" ]; then
      continue
    fi
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
      printf '[stop] %s pid=%s\n' "$api_name" "$pid"
      kill "$pid" 2>/dev/null || true
      for _ in 1 2 3 4 5; do
        kill -0 "$pid" 2>/dev/null || break
        sleep 1
      done
      kill -0 "$pid" 2>/dev/null && kill -9 "$pid" 2>/dev/null || true
      stopped=$((stopped + 1))
    fi
    rm -f "$pid_file"
  done
  printf '[stop] stopped=%s\n' "$stopped"
}

start_apis() {
  mkdir -p "$PID_DIR" "$LOG_DIR"
  export PYTHONPATH="$APIS_DIR:${PYTHONPATH:-}"

  local started=0
  for layer in exposed internal; do
    [ -d "$APIS_DIR/$layer" ] || continue
    for api_dir in "$APIS_DIR/$layer"/*/; do
      [ -d "$api_dir" ] || continue
      local api_name
      api_name="$(basename "$api_dir")"
      [ "$api_name" = "shared" ] && continue
      [ "$api_name" = "__pycache__" ] && continue
      if [ -n "$filter" ] && [ "$api_name" != "$filter" ]; then
        continue
      fi
      if [ ! -x "$api_dir/run_api.sh" ]; then
        printf '[skip] %s/%s missing run_api.sh\n' "$layer" "$api_name"
        continue
      fi

      printf '[start] %s/%s\n' "$layer" "$api_name"
      (cd "$api_dir" && ./run_api.sh) > "$LOG_DIR/$api_name.log" 2>&1 &
      echo "$!" > "$PID_DIR/$api_name.pid"
      started=$((started + 1))
    done
  done

  printf '[start] started=%s logs=%s\n' "$started" "$LOG_DIR"
  [ "$started" -gt 0 ] || exit 1
}

case "$command" in
  stop)
    stop_apis
    ;;
  restart)
    stop_apis
    start_apis
    ;;
  start)
    start_apis
    ;;
esac
