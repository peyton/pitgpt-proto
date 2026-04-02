#!/usr/bin/env bash
# Prompt for missing environment variables instead of letting mise template errors crash.

if [ -z "${OPENROUTER_API_KEY:-}" ]; then
  if [ -t 0 ]; then
    printf "OPENROUTER_API_KEY is not set. Enter it now: " >&2
    read -r OPENROUTER_API_KEY
    export OPENROUTER_API_KEY
  else
    echo "warning: OPENROUTER_API_KEY is not set (non-interactive session, skipping prompt)" >&2
  fi
fi
