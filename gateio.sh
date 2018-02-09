#!/bin/bash
until gateio.py; do
    echo "'gateio.py' crashed with exit code $?. Restarting..." >&2
    sleep 1
done