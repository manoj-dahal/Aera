# AERA Agent — common dev tasks.
#
# Quick commands:
#   make run         launch AERA GUI
#   make cli         launch AERA in terminal
#   make install     pip-install runtime deps
#   make dev         pip-install dev + runtime deps
#   make build       build standalone executable for current OS
#   make installer   also build OS-specific installer (exe/dmg/AppImage)
#   make clean       remove build artifacts

PYTHON ?= python3

.PHONY: run cli install dev build installer desktop light-desktop clean test

run:
	$(PYTHON) -m aera_agent gui

cli:
	$(PYTHON) -m aera_agent cli

install:
	$(PYTHON) -m pip install -r requirements.txt

dev:
	$(PYTHON) -m pip install -e ".[piper,build]" pytest

build:
	$(PYTHON) build_tools/build.py

installer:
	$(PYTHON) build_tools/build.py --installer

desktop:
	# Full self-contained desktop bundle (249MB, includes PySide6)
	$(PYTHON) -m pip install shiv --quiet
	shiv -c aera-gui -o dist/AERA.pyz . --reproducible --compressed
	mkdir -p dist/AERA-Desktop-App
	cp dist/AERA.pyz dist/AERA-Desktop-App/AERA-full.pyz
	cp assets/aera_icon.png assets/aera_icon.ico dist/AERA-Desktop-App/ 2>/dev/null || true
	@echo '#!/bin/bash\nDIR="$$(cd "$$(dirname "$$0")" && pwd)"\nexec python3 "$$DIR/AERA-full.pyz" "$$@"' > dist/AERA-Desktop-App/AERA
	chmod +x dist/AERA-Desktop-App/AERA
	@echo '[Desktop Entry]\nName=AERA Agent\nExec=./AERA\nIcon=aera_icon.png\nType=Application' > dist/AERA-Desktop-App/AERA.desktop

light-desktop:
	# Lightweight zipapp (244K, needs pip deps: PySide6 openai psutil)
	python3 -m zipapp /tmp/zipsrc -p "/usr/bin/env python3" -o dist/AERA-light.pyz --compress 2>/dev/null || \
	$(PYTHON) -m zipapp -c -m "aera_agent.gui.app:main" -p "/usr/bin/env python3" -o dist/AERA-light.pyz aera_agent 2>/dev/null || \
	shiv -c aera-gui -o dist/AERA-light.pyz . --no-modify --reproducible --compressed || true
	@echo "Built dist/AERA-light.pyz"

clean:
	rm -rf build dist *.spec aera_agent/**/__pycache__ aera_agent/__pycache__ aera_agent.egg-info

test:
	$(PYTHON) -m pytest -v
