#!/usr/bin/env bash

#!/usr/bin/env bash
# parse_dng_args.sh
# Simple argument parser for a required DNG file and optional test/workspace path.
# Usage examples:
#   ./parse_dng_args.sh /path/to/file.dng
#   ./parse_dng_args.sh --test-path=/tmp/workspace /path/to/file.dng
#   ./parse_dng_args.sh --test-path /tmp/workspace /path/to/file.dng
#   ./parse_dng_args.sh test-path=/tmp/workspace /path/to/file.dng

#set -Eeuo pipefail

cleanup-mounted-dng(){
  local path="$1"
  if [ -d "$path" ]; then
    hdiutil detach "$path" -force
  fi
}

test-speedwagon-contrib-installed(){
  local SPEEDWAGON_EXEC="$1"
  local $SPEEDWAGON_STDERR

  SPEEDWAGON_STDERR=$(mktemp)
  if "$SPEEDWAGON_EXEC" info --format=json 2> "$SPEEDWAGON_STDERR" | jq -e '.installed_packages | any(startswith("speedwagon-contrib"))' > /dev/null; then
    rm "$SPEEDWAGON_STDERR"
    return 0
  else
    cat "$SPEEDWAGON_STDERR"
    rm "$SPEEDWAGON_STDERR"
    return 1
  fi
}

test-speedwagon-can-run-version(){
  local SPEEDWAGON_EXEC=$1
  local SPEEDWAGON_STDERR

  SPEEDWAGON_STDERR=$(mktemp)
  if "$SPEEDWAGON_EXEC" --version 2> "$SPEEDWAGON_STDERR"; then
    rm "$SPEEDWAGON_STDERR"
    return 0
  else
    cat "$SPEEDWAGON_STDERR"
    rm "$SPEEDWAGON_STDERR"
    return 1
  fi
}

test-dng() {
  local dngFile="$1"
  local mountpoint="$2"
  local RC=0

  if hdiutil verify "$dngFile" ; then
    echo "TEST: verify DNG - success."
  else
    echo "TEST: verify DNG - failed."
    RC=1
  fi

  hdiutil attach "$dngFile" -mountpoint "$mountpoint" -quiet -noverify -readonly
  trap "cleanup-mounted-dng \"$mountpoint\" -force; $(trap -p EXIT | cut -d"'" -f2)" EXIT

  if test-speedwagon-can-run-version "$mountpoint/Speedwagon (UIUC Prescon Edition).app/Contents/MacOS/speedwagon" ; then
    echo 'TEST: speedwagon has a version  - success'
  else
    echo 'TEST: speedwagon has a version - failed'
    RC=1
  fi

  if test-speedwagon-contrib-installed "$mountpoint/Speedwagon (UIUC Prescon Edition).app/Contents/MacOS/speedwagon" ; then
    echo 'TEST: speedwagon-contrib installed - success'
  else
    echo 'TEST: speedwagon-contrib installed - failed'
    RC=1
  fi

  return $RC
}

usage() {
  cat <<EOF
Usage: $0 [OPTIONS] DNG_FILE

Positional arguments:
  DNG_FILE                Path to the required .dng file

Options (optional):
  --test-path PATH        Set a testing/workspace path

  -h, --help              Show this help message and exit

Examples:
  $0 /tmp/image.dng
  $0 --test-path=/tmp/work /tmp/image.dng
  $0 --test-path /tmp/work /tmp/image.dng
  $0 test-path=/tmp/work /tmp/image.dng
EOF
}

# Defaults
TEST_PATH=""
DNG_FILE=""

# Parse args
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)
      usage
      exit 0
      ;;
    --test-path=*)
      TEST_PATH="${1#*=}"
      shift
      ;;
    --test-path)
      if [[ $# -lt 2 ]]; then
        echo "Error: --test-path requires an argument." >&2
        usage
        exit 2
      fi
      TEST_PATH="$2"
      shift 2
      ;;
    test-path=*)
      TEST_PATH="${1#*=}"
      shift
      ;;
    --) # end of options
      shift
      break
      ;;
    -*)
      echo "Unknown option: $1" >&2
      usage
      exit 3
      ;;
    *)
      # first non-option is the DNG file (required)
      if [[ -z "$DNG_FILE" ]]; then
        DNG_FILE="$1"
        shift
      else
        echo "Unexpected positional argument: $1" >&2
        usage
        exit 4
      fi
      ;;
  esac
done

# If there are any remaining positional args after parsing, treat the first as DNG if not set
if [[ -z "$DNG_FILE" && $# -gt 0 ]]; then
  DNG_FILE="$1"
  shift
fi

# Validate required DNG file
if [[ -z "$DNG_FILE" ]]; then
  echo "Error: DNG_FILE is required." >&2
  usage
  exit 5
fi

# Optional: verify file exists (comment out if you don't want this check)
if [[ ! -e "$DNG_FILE" ]]; then
  echo "Warning: DNG file '$DNG_FILE' does not exist (or path is wrong)." >&2
  # not exiting; keep as warning. If you prefer to enforce existence, change to exit 6
fi

# Output parsed values (for consumers or testing)
echo "DNG_FILE='$DNG_FILE'"
if [[ -n "$TEST_PATH" ]]; then
  echo "TEST_PATH='$TEST_PATH'"
else
  echo "TEST_PATH is not set"
fi


if [ -z "$TEST_PATH" ]; then
  TEST_PATH=$(mktemp -d)
  trap 'rm -rf $TEST_PATH' EXIT
fi

if [ ! -d "$TEST_PATH" ]; then
  echo "$TEST_PATH does not exist"
  exit 1
fi

echo "using $TEST_PATH"
test-dng "$DNG_FILE" "$TEST_PATH/macos_apps"
status=$?

echo
if [ "$status" -eq 0 ]; then
  echo "Testing $DNG_FILE - success"
else
  echo "Testing $DNG_FILE - failed"
fi
exit $status
