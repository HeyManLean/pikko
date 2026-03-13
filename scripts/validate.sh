#!/usr/bin/env bash
set -euo pipefail

echo "Running ruff check..."
ruff check .

echo "Running mypy..."
mypy .

echo "All checks passed."
