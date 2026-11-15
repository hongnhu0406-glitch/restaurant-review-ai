#!/usr/bin/env bash
set -e
export PYTHONUTF8=1
export PYTHONIOENCODING=utf-8
cd "$(dirname "$0")"
python start_app.py
