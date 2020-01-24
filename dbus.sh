#!/bin/bash

set -ex

SCRIPT_PATH=$(dirname "${0}")

source "${SCRIPT_PATH}/venv/bin/activate"

python3 "${SCRIPT_PATH}/holdthedoor.py" &

while sleep 1; do
    python3 "${SCRIPT_PATH}/dbus-service.py"
    echo "====restart==="
done
