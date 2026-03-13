#!/usr/bin/env bash
set -euo pipefail

echo "Running ruff format..."
ruff format .

echo "Running ruff check --fix..."
ruff check --fix .

echo "Done."
