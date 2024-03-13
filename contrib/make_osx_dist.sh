#!/usr/bin/env bash
set -e
BUILD_PATH=./build/build_speedwagon
VENV_PATH_FREEZE=$BUILD_PATH/venv_freeze_speedwagon
VENV_PATH_BUILD=$BUILD_PATH/venv_build_workflows_package
DIST_PATH=$BUILD_PATH/packaging
BASE_PYTHON=python3.11
WHEEL_NAME=
INSTALLING_PYTHON_PACKAGE_NAME=speedwagon-uiucprescon
APP_NAME='Speedwagon (UIUC Prescon Prerelease)'

usage() {
    cat << EOF
    Usage for building standalone app for Mac

    ${0} [--using-wheel PATH_TO_WHL_FILE] [--base-python PATH_TO_PYTHON_EXECUTABLE] [--build-path PATH]
EOF
}

build_wheel() {
    if [ ! -d "$VENV_PATH_BUILD" ]
    then
        $BASE_PYTHON -m venv $VENV_PATH_BUILD
        $VENV_PATH_BUILD/bin/python -m pip install pip --upgrade
        $VENV_PATH_BUILD/bin/python -m pip install build
    fi
    $VENV_PATH_BUILD/bin/python -m build --outdir $DIST_PATH --wheel
    wheel_files=($DIST_PATH/*.whl)
    WHEEL_NAME=${wheel_files[0]}
}

create_build_env() {
    if [ ! -d "$VENV_PATH_FREEZE" ]
    then
        $BASE_PYTHON -m venv $VENV_PATH_FREEZE
        $VENV_PATH_FREEZE/bin/python -m pip install pip --upgrade
        $VENV_PATH_FREEZE/bin/pip install -r requirements-mac-dmg.txt
    fi
}

install_current_distribution() {
    $VENV_PATH_FREEZE/bin/pip install $WHEEL_NAME --force-reinstall
}

create_apple_bundle() {
    echo "Creating Apple Bundle"
    $VENV_PATH_FREEZE/bin/python packaging/create_osx_app_bundle.py $INSTALLING_PYTHON_PACKAGE_NAME --app-name="$APP_NAME.app"
    echo -e "\n\nCreating Apple Bundle - Done. The following are the files created along with their SHA-256 hash value.\n"
    for bundleFile in ./dist/*.dmg; do
        shasum -a 256 "${bundleFile}"
    done;
}

main() {
    if ! [ -f "${WHEEL_NAME}" ]
        then
            echo "Creating distribution wheel"
            build_wheel
        else
            echo "Using $WHEEL_NAME"
    fi
    create_build_env
    install_current_distribution
    create_apple_bundle
}

while [[ "${#}" -gt 0 ]]; do
    case "${1}" in
        -h|--help)
            usage
            exit 0
            ;;
        --using-wheel)
            WHEEL_NAME="${2:-}"
            shift 2
            ;;
        --base-python)
            BASE_PYTHON="${2:-}"
            shift 2
            ;;
        --build-path)
            BUILD_PATH="${2:-}"
            shift 2
            ;;
        *)
            echo "invalid arguments"
            usage
            exit 1
            ;;
    esac
done

main
