#!/usr/bin/env bash
# Launcher for Super Block Bros
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
    echo "Setting up venv..."
    python3 -m venv .venv
    .venv/bin/pip install --quiet pygame
fi
exec .venv/bin/python mario.py
