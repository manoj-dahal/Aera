#!/usr/bin/env bash
# AERA Agent build helper for Linux / macOS.
#
# Usage:   bash build_tools/build.sh           # standalone bundle
#          bash build_tools/build.sh installer # also build DMG / AppImage
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON=${PYTHON:-python3}

echo "================================"
echo "  Building AERA Agent"
echo "  Python: $($PYTHON --version)"
echo "  OS:     $(uname -s) $(uname -m)"
echo "================================"

if [ "${1:-}" = "installer" ]; then
    $PYTHON build_tools/build.py --installer
else
    $PYTHON build_tools/build.py
fi

echo
echo "Run AERA with:   ./dist/AERA/AERA"
[ -d dist/AERA.app ] && echo "Or open:         open dist/AERA.app"
