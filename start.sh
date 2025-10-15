#!/bin/sh

set -euo pipefail

log() {
    printf '[start.sh] %s\n' "$1"
}

REQUIRED_VARS="
NEXT_PUBLIC_SUPABASE_URL
TELEGRAM_BOT_TOKEN
OPENAI_API_KEY
BASE_URL
"
missing=0

for var in $REQUIRED_VARS; do
    value=$(eval "printf '%s' \"\${$var:-}\"")
    if [ -z "$value" ]; then
        log "ERROR: $var is not set"
        missing=1
    else
        length=${#value}
        log "INFO: $var is set (length $length)"
    fi
done

if [ -z "${SUPABASE_SERVICE_ROLE_KEY:-}" ]; then
    if [ -n "${NEXT_PUBLIC_SUPABASE_ANON_KEY:-}" ]; then
        fallback_len=${#NEXT_PUBLIC_SUPABASE_ANON_KEY}
        log "WARNING: SUPABASE_SERVICE_ROLE_KEY missing, using NEXT_PUBLIC_SUPABASE_ANON_KEY (length $fallback_len)"
    else
        log "ERROR: Neither SUPABASE_SERVICE_ROLE_KEY nor NEXT_PUBLIC_SUPABASE_ANON_KEY is set"
        missing=1
    fi
else
    service_len=${#SUPABASE_SERVICE_ROLE_KEY}
    log "INFO: SUPABASE_SERVICE_ROLE_KEY is set (length $service_len)"
fi

if [ "$missing" -ne 0 ]; then
    log "FATAL: Missing required configuration. Refusing to start."
    exit 1
fi

log "Starting SkinTracker on port ${PORT:-8080}"
exec uvicorn server:app \
    --host 0.0.0.0 \
    --port "${PORT:-8080}" \
    --log-level info \
    --access-log