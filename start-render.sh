#!/bin/bash
# Optimized start script for Render free tier (512MB RAM)

# Disable heavy features to save memory
export ENABLE_AI_DENOISE=false
export ENABLE_STEMS=false  
export ENABLE_TRANSCRIPTION=false

# Single worker to minimize memory
export WEB_CONCURRENCY=1
export WORKERS=1

# Start with minimal memory footprint
cd src && exec uvicorn noise_cleaner.app:app \
  --host 0.0.0.0 \
  --port ${PORT:-8000} \
  --workers 1 \
  --no-access-log \
  --log-level warning
