#!/bin/bash
# v∞ 本地心跳脚本
set -e
cd /tmp/vinf_repo || exit 1
python3 vinf_console.py verify
python3 vinf_console.py tick
python3 vinf_console.py bundle
git add -A
git commit -m "[v∞] local heartbeat $(date +%Y-%m-%d-%H:%M)" || true
git push origin main || true
