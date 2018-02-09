#!/bin/bash
until poloniex.py; do
    echo "'poloniex.py' crashed with exit code $?. Restarting..." >&2
    sleep 1
done