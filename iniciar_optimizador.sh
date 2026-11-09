#!/usr/bin/env bash
# Script lanzador para Linux
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"
cd "$DIR"

# Verificar python3 y dependencias
if ! command -v python3 &> /dev/null; then
    echo "Python3 no está instalado. Instálalo con: sudo apt install python3 python3-tk"
    exit 1
fi

python3 gui_app.py
