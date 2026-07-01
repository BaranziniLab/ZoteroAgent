#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf dist
mkdir -p dist
zip -qr "dist/zoteroagent.brxt" manifest.json README.md LICENSE NOTICE pyproject.toml uv.lock src skills
echo "dist/zoteroagent.brxt"
