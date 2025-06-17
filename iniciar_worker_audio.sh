#!/bin/bash
cd "$(dirname "$0")/.."
source venv/bin/activate
celery -A worker.celery_app worker -Q transcripciones --loglevel=info --concurrency=2
