#!/usr/bin/env bash
# AERA Agent build helper for Linux / macOS.
#
# Usage:
#   bash build_tools/build.sh                    # onedir bundle (dist/AERA/)
#   bash build_tools/build.sh --onefile          # single file exe (dist/AERA)
#   bash build_tools/build.sh --installer        # + AppImage/Deb/DMG/Pkg
#   bash build_tools/build.sh --all              # onedir + onefile + pyz + zips + installers
#   bash build_tools/build.sh --help
set -euo pipefail

cd "$(dirname "$0")/.."

PYTHON=${PYTHON:-python3}

echo "================================"
echo "  Building AERA Agent"
echo "  Python: $($PYTHON --version)"
echo "  OS:     $(uname -s) $(uname -m)"
echo "  Args:   ${*:-<none>}"
echo "================================"

# Forward all args to build.py
$PYTHON build_tools/build.py "$@"

echo
echo "Outputs in ./dist/:"
ls -lh dist/ 2>/dev/null | tail -n 50 || true
echo
if [ -f dist/AERA/AERA ]; then echo "Run Linux:   ./dist/AERA/AERA"; fi
if [ -d dist/AERA.app ]; then echo "Run macOS:   open dist/AERA.app"; fi
if [ -f dist/AERA.exe ]; then echo "Run Windows onefile: ./dist/AERA.exe"; fi
if [ -f dist/AERA.pyz ]; then echo "Run pyz:     python3 dist/AERA.pyz"; fi
if [ -f dist/AERA-x86_64.AppImage ]; then echo "AppImage:    ./dist/AERA-x86_64.AppImage"; fi
if ls dist/AERA*.dmg 1>/dev/null 2>&1; then echo "DMG:         dist/AERA*.dmg"; fi
if ls dist/AERA*.deb 1>/dev/null 2>&1; then echo "DEB:         dist/*.deb -> sudo dpkg -i"; fi
