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

.PHONY: run cli install dev build installer clean test

run:
	$(PYTHON) -m aera_agent gui

cli:
	$(PYTHON) -m aera_agent cli

install:
	$(PYTHON) -m pip install -r requirements.txt

dev:
	$(PYTHON) -m pip install -e ".[piper]" pyinstaller pillow cairosvg pytest

build:
	$(PYTHON) build_tools/build.py

installer:
	$(PYTHON) build_tools/build.py --installer

clean:
	rm -rf build dist *.spec aera_agent/**/__pycache__ aera_agent/__pycache__

test:
	$(PYTHON) -m pytest -v
