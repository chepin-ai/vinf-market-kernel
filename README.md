# v∞ Market Kernel — 自演化理论内核的单一事实源

[![v∞-heartbeat](../../actions/workflows/heartbeat.yml/badge.svg)](../../actions/workflows/heartbeat.yml)
[![v∞-finance-daily](../../actions/workflows/finance-daily.yml/badge.svg)](../../actions/workflows/finance-daily.yml/badge.svg)
[![v∞-watchdog](../../actions/workflows/watchdog.yml/badge.svg)](../../actions/workflows/watchdog.yml)

三条时间线（本体沙箱 / 手机心跳 / GitHub Actions）经本仓库并轨，Git-first 协议，哈希链只增不减。

- `journal39.jsonl` — 防篡改哈希链日志（prev_hash→hash）
- `theory_db.sqlite` — 定理/前沿/债务/预测记忆库
- `state_bundle.json` — Dashboard 单一数据契约
- `strategies.json` — T33 策略台账（CI 日更实测指标）
- `ci_tick.py / ci_finance.py / ci_watchdog.py` — Actions 三引擎
- `WATCHDOG.md` — 看门狗周报（断链/失联 → 红徽章报警）

密钥与大数据永不出境（.gitignore）；CI 无密钥时自动降级为无 LLM 模式。
