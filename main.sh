#!/bin/bash

CMD=$1

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

PY_PATH="${SCRIPT_DIR}/server.py"
LOG_PATH="${SCRIPT_DIR}/logs/server.log"
ERR_PATH="${SCRIPT_DIR}/logs/server.error"

source ~/miniconda3/etc/profile.d/conda.sh
conda activate base

if [ -z "${CMD}" ]
then
    echo "please provide argument: [start | stop | restart]"
else
    case "${CMD}" in 
        "start") nohup python "${PY_PATH}" start  1>>"${LOG_PATH}" 2>>"${ERR_PATH}" &
            echo "started"
        ;;
        "stop") python "${PY_PATH}" stop
        ;;
        "restart") python "${PY_PATH}" stop
                nohup python "${PY_PATH}" start 1>>"${LOG_PATH}" 2>>"${ERR_PATH}" &
                echo "started"
        ;;
        "show") python "${PY_PATH}" show
        ;;
        *) echo "valid argument: [start | stop | restart]"
        ;;
    esac
fi