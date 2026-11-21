#!/bin/sh
set -eu

root=$(CDPATH= cd "$(dirname "$0")" && pwd)
project="$root/src/dependency_graph_lab"

if command -v python3 >/dev/null 2>&1; then
    interpreter=python3
else
    interpreter=python
fi

if [ "$#" -eq 0 ]; then
    set -- -p A --test -r "$project/example_repository.json" -d 4 --ascii
fi

exec "$interpreter" -B "$project/dependency_graph.py" "$@"
