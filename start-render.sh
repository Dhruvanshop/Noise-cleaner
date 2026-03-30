#!/bin/sh
# Ultra-simple start script for Render free tier

# Disable all heavy features
export ENABLE_AI_DENOISE=false
export ENABLE_STEMS=false  
export ENABLE_TRANSCRIPTION=false
export WEB_CONCURRENCY=1

# Start with single worker
exec uvicorn noise_cleaner.app:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
