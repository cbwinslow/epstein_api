#!/bin/bash
#
# Launch Wrapper for Master Orchestrator
#
# Usage:
#   ./launch.sh
#
# This thin wrapper invokes the orchestrate.py using uv run,
# ensuring dependencies are managed via uv.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$SCRIPT_DIR"

echo "Launching Master Orchestrator..."
echo ""

exec uv run python orchestrate.py "$@"
