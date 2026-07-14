# AERA Agent — common dev tasks & cross-platform packaging
#
# Run:
#   make run            launch GUI
#   make cli            terminal
#   make build          onedir bundle via PyInstaller (dist/AERA/)
#   make onefile        single-file exe (dist/AERA / dist/AERA.exe)
#   make desktop        full self-contained pyz (249MB, includes PySide6) via shiv
#   make light-desktop  lightweight pyz (244K, needs pip deps)
#   make installer      OS-specific installer (Setup.exe / DMG / AppImage / DEB)
#   make all-dist       onedir + onefile + pyz + portable zips + installer
#   make deb            Linux .deb package (needs dpkg-deb)
#   make appimage       Linux AppImage (needs appimagetool)
#   make dmg            macOS DMG (needs create-dmg, macOS only)
#   make pkg            macOS PKG (needs pkgbuild, macOS only)
#   make exe            Windows Setup.exe (needs iscc / Inno Setup, Windows only)
#   make msi            Windows MSI (needs WiX candle+light, Windows only)
#   make clean

PYTHON ?= python3

.PHONY: run cli install dev build onefile installer all-dist desktop light-desktop exe msi deb appimage dmg pkg clean test pyz wheel

run:
	$(PYTHON) -m aera_agent gui

cli:
	$(PYTHON) -m aera_agent cli

install:
	$(PYTHON) -m pip install -e .

dev:
	$(PYTHON) -m pip install -e ".[audio,piper,build]" pytest ruff mypy
	$(PYTHON) -m pip install shiv

build:
	$(PYTHON) build_tools/build.py

onefile:
	$(PYTHON) build_tools/build.py --onefile

installer:
	$(PYTHON) build_tools/build.py --installer

all-dist:
	$(PYTHON) build_tools/build.py --all

# --- shiv pyz (fallback, no libpython needed) ---
pyz:
	$(PYTHON) -m pip install shiv --quiet
	shiv -c aera-gui -o dist/AERA.pyz . --reproducible --compressed
	shiv -c aera-cli -o dist/AERA-cli.pyz . --reproducible --compressed
	ls -lh dist/*.pyz

wheel:
	$(PYTHON) -m build --wheel --sdist --outdir dist
	ls -lh dist/*.whl dist/*.tar.gz

desktop:
	# Full self-contained desktop bundle (249MB, includes PySide6)
	$(PYTHON) -m pip install shiv --quiet
	shiv -c aera-gui -o dist/AERA.pyz . --reproducible --compressed
	mkdir -p dist/AERA-Desktop-App
	cp dist/AERA.pyz dist/AERA-Desktop-App/AERA-full.pyz
	cp assets/aera_icon.png assets/aera_icon.ico dist/AERA-Desktop-App/ 2>/dev/null || true
	@echo '#!/bin/bash\nDIR="$$(cd "$$(dirname "$$0")" && pwd)"\nexec python3 "$$DIR/AERA-full.pyz" "$$@"' > dist/AERA-Desktop-App/AERA
	chmod +x dist/AERA-Desktop-App/AERA
	@echo '[Desktop Entry]\nName=AERA Agent\nExec=./AERA\nIcon=aera_icon.png\nType=Application\nCategories=Utility;' > dist/AERA-Desktop-App/AERA.desktop
	@echo "Desktop app built in dist/AERA-Desktop-App/"

light-desktop:
	# Lightweight zipapp (244K, needs pip deps: PySide6 openai psutil)
	mkdir -p /tmp/zipsrc && rm -rf /tmp/zipsrc/*
	cp -r aera_agent omnivoice /tmp/zipsrc/ 2>/dev/null || true
	cp aera.py /tmp/zipsrc/__main__.py
	$(PYTHON) -m zipapp /tmp/zipsrc -p "/usr/bin/env python3" -o dist/AERA-light.pyz --compress
	@echo "Built dist/AERA-light.pyz (lightweight)"

# --- OS-specific ---
exe:
	$(PYTHON) build_tools/build.py --no-install-deps --no-icons --installer
	@echo "Windows Setup.exe should be in dist/ if iscc found"

msi:
	@echo "Building MSI requires WiX Toolset (candle + light) on Windows"
	$(PYTHON) build_tools/build.py --no-install-deps --no-icons --installer

deb:
	$(PYTHON) build_tools/build.py --no-install-deps --no-icons --installer
	@echo "DEB should be in dist/ if dpkg-deb found"

appimage:
	$(PYTHON) build_tools/build.py --no-install-deps --no-icons --installer
	@echo "AppImage should be in dist/ if appimagetool found"

dmg:
	$(PYTHON) build_tools/build.py --no-install-deps --no-icons --installer
	@echo "DMG should be in dist/ if create-dmg found (macOS only)"

pkg:
	$(PYTHON) build_tools/build.py --no-install-deps --no-icons --installer
	@echo "PKG should be in dist/ if pkgbuild found (macOS only)"

clean:
	rm -rf build dist *.spec aera_agent/**/__pycache__ aera_agent/__pycache__ aera_agent.egg-info __pycache__

test:
	$(PYTHON) -m pytest -v
