#!/usr/bin/env bash
set -e

INSTALLED_UV=$(command -v uv)
scriptDir=$(dirname -- "$(readlink -f -- "$BASH_SOURCE")")
project_root=$(realpath "$scriptDir/..")
APP_NAME='Speedwagon (UIUC Prescon Edition)'
BOOTSTRAP_SCRIPT="${project_root}/contrib/speedwagon_bootstrap.py"
PACKAGE_SPEEDWAGON_SCRIPT_URL="https://github.com/UIUCLibrary/speedwagon_scripts/archive/refs/tags/v0.1.4.tar.gz"

install_temporary_uv(){
    venvPath=$1
    $DEFAULT_BASE_PYTHON -m venv $venvPath
    trap "rm -rf $venvPath" EXIT
    $venvPath/bin/pip install --disable-pip-version-check uv
}

generate_release_with_uv(){
   local uv=$1
   local project_root=$2
   local wheel=$3
   local python_version=$4
    if [ "$python_version" = "" ]
    then
        echo "generate_release_with_uv() failed: No python version specified"
        print_usage
        exit 1
    fi
    local build_path
    build_path=$(mktemp -d)

    $uv export ${python_version:+--python=$python_version} --format pylock.toml --extra gui --extra contrib --no-dev --no-emit-project --output-file ${build_path}/pylock.toml
    $uv tool run --python=${python_version} --from package-speedwagon@${PACKAGE_SPEEDWAGON_SCRIPT_URL} package_speedwagon $wheel -r ${build_path}/pylock.toml --app-name="${APP_NAME}" --app-bootstrap-script="${BOOTSTRAP_SCRIPT}" --hidden-import='speedwagon_contrib'

}

print_usage(){
    echo "Usage: $0 [options] wheel"
}

show_help() {
    print_usage
    echo
    echo "Arguments:"
    echo "  wheel            Python (.whl) Wheel file  to use. "
    echo
    echo "Options:"
    echo "  --python-version=VERSION Python version to use (default: 3.12+gil)"
    echo "  --help           Display this help message and exit."
}

python_version=""

while [[ $# -gt 0 ]]; do
  case $1 in
    --python-version=*)
      python_version="${1#*=}"
      shift
      ;;
    --python-version)
      python_version="$2"
      shift 2
      ;;
    --help|-h)
      show_help
      exit 0
      ;;
    -*)
      echo "Unknown option: $1"
      print_usage
      exit 1
      ;;
    *)
      wheel="$1"
      shift
      break
      ;;
  esac
done

if [ -z "$wheel" ]; then
  echo "Error: Missing wheel argument."
  print_usage
  exit 1
fi

echo "wheel = $wheel"
if [[ ! -f "$INSTALLED_UV" ]]; then
    tmpdir=$(mktemp -d)
    install_temporary_uv $tmpdir
    uv=$tmpdir/bin/uv
else
    uv=$INSTALLED_UV
fi

generate_release_with_uv "$uv" "$project_root" "$wheel" "$python_version"
