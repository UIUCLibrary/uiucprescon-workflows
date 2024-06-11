#!/usr/bin/env bash
path=$(dirname "$0")
BASE_PYTHON=python3
PYTHON_SCRIPT=$(dirname "$0")/../packaging/package_speedwagon.py
BUILD_VENV=build/build_standalone_build_env
$BASE_PYTHON -m venv $BUILD_VENV
. $BUILD_VENV/bin/activate
python -m pip install pip --upgrade
python -m pip install PyInstaller cmake
python $PYTHON_SCRIPT $@
