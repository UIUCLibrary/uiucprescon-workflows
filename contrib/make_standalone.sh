#!/usr/bin/env bash
set -e

PYTHON_SCRIPT=$(dirname "$0")/../packaging/package_speedwagon.py
DEFAULT_BUILD_VENV=build/build_standalone_build_env
build_venv=$DEFAULT_BUILD_VENV

default_python_path=$(which python3)
python_path=$default_python_path

create_venv() {
    base_python_path=$1
    venv_path=$2
    $base_python_path -m venv $venv_path
    . $venv_path/bin/activate
    python -m pip install pip --upgrade
    python -m pip install PyInstaller cmake
    deactivate
}

create_standalone(){
    venv_path=$1
    shift;
    script_args=$@
    . $venv_path/bin/activate
    $venv_path/bin/python $PYTHON_SCRIPT $script_args
    deactivate
}

display_help() {
    echo "Usage: $0 [OPTIONS] python_package_file [SCRIPT_OPTIONS]"
    echo "Options:"
    echo "  --base-python-path PATH   Specify the path to the Python interpreter (default: $default_python_path)"
    echo "  --venv-path PATH          Specify the path to the Python interpreter (default: $DEFAULT_BUILD_VENV)"
    echo "  --help                    Display this help message"
    if [[ -e "$BUILD_VENV/bin/python" ]]; then
        $BUILD_VENV/bin/python $PYTHON_SCRIPT --help
    fi
    exit 0
}
# Parse optional arguments
while [[ $# -gt 0 ]]; do
    key="$1"
    case $key in
        --base-python-path)
            python_path="$2"
            shift
            shift
            ;;
        --venv-path)
            build_venv="$2"
            shift
            shift
            ;;
        --help)
            display_help
            ;;
        *)
            break;
            ;;
    esac
done

# Print the selected Python path
echo "Using Python from: $python_path"
if [[ ! -e "$build_venv" ]]; then
    create_venv $python_path $build_venv
fi
create_standalone $build_venv $@
# python $PYTHON_SCRIPT $@