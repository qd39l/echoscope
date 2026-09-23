#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
revision=01d5d2814fa9dd61e9d211e0b235a4a592a9316a
if [[ ! -d tt/.git ]]; then
  git clone https://github.com/TinyTapeout/tt-support-tools.git tt
fi
git -C tt checkout "$revision"
uv venv --python 3.11 .venv
uv pip install --python .venv/bin/python -r test/requirements.txt -r tt/requirements.txt librelane==3.0.14
