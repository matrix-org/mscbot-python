#!/bin/sh
# Lints the codebase

files="./*.py scripts/ scripts-dev/"
isort $files
black $files
flake8 $files
