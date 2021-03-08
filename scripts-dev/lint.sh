#!/bin/sh
# Lints the codebase
isort ./*.py
black ./*.py
flake8 ./*.py
