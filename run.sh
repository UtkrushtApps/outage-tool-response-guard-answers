#!/usr/bin/env bash
set -uo pipefail
cd /root/task
python -m pip install -q -r requirements.txt

echo "Checking imports and configuration..."
python - <<'PY'
from dotenv import load_dotenv

load_dotenv('/root/task/.env')
from agent.config import load_config
from agent.tools import OUTAGE_STATUS_TOOL

config = load_config(require_key=False)
if not config.model:
    raise RuntimeError('Agent model is not configured')
if OUTAGE_STATUS_TOOL.get('type') != 'function':
    raise RuntimeError('Tool schema is not ready')
print('Key-free readiness check passed.')
PY

echo "Running offline tests..."
python -m pytest -q
rc=$?
if [ "$rc" -le 1 ]; then
  echo "Repository is ready. Test failures may describe the candidate work."
  exit 0
else
  echo "Readiness failed because tests could not execute correctly."
  exit "$rc"
fi
