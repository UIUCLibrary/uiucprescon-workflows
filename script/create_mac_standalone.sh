#!/usr/bin/env bash
set -e

INSTALLED_UV=$(command -v uv)
scriptDir=$(dirname -- "$(readlink -f -- "$BASH_SOURCE")")
project_root=$(realpath "$scriptDir/..")
APP_NAME='Speedwagon (UIUC Prescon Edition)'
BOOTSTRAP_SCRIPT="${project_root}/contrib/speedwagon_bootstrap.py"
PACKAGE_SPEEDWAGON_SCRIPT_URL="https://github.com/UIUCLibrary/speedwagon_scripts/archive/refs/tags/v0.1.0.tar.gz"

install_temporary_uv(){
    venvPath=$1
    $DEFAULT_BASE_PYTHON -m venv $venvPath
    trap "rm -rf $venvPath" EXIT
    $venvPath/bin/pip install --disable-pip-version-check uv
}

generate_release_with_uv(){
    uv=$1
    project_root=$2
    wheel=$3

    local build_path
    build_path=$(mktemp -d)
    $uv export --no-hashes --format requirements-txt --extra gui --no-dev --no-emit-project > ${build_path}/requirements-gui.txt
    $uv tool run --from package_speedwagon@${PACKAGE_SPEEDWAGON_SCRIPT_URL} package_speedwagon $wheel -r ${build_path}/requirements-gui.txt --app-name="${APP_NAME}" --app-bootstrap-script="${BOOTSTRAP_SCRIPT}"

}

print_usage(){
    echo "Usage: $0 wheel [--help]"
}

show_help() {
    print_usage
    echo
    echo "Arguments:"
    echo "  wheel            Python (.whl) Wheel file  to use. "
    echo
    echo "Options:"
    echo "  --help           Display this help message and exit."
}
# Check if the help flag is provided
for arg in "$@"; do
    if [[ "$arg" == "--help" || "$arg" == "-h" ]]; then
    show_help
    exit 0
  fi
done

if [ -z "$1" ]; then
  echo "Error: Missing required arguments."
  print_usage
  exit 1
fi

wheel=$1
echo "wheel = $wheel"
if [[ ! -f "$INSTALLED_UV" ]]; then
    tmpdir=$(mktemp -d)
    install_temporary_uv $tmpdir
    uv=$tmpdir/bin/uv
else
    uv=$INSTALLED_UV
fi

generate_release_with_uv "$uv" "$project_root" "$wheel"
