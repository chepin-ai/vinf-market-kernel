# -*- coding: utf-8 -*-
"""v∞ CI心跳 (第47章) — GitHub Actions 版 tick
与沙箱cron心跳同一协议: Git-first(Actions checkout即restore) → verify → tick → journal续链 → bundle。
区别: 提交推送由workflow层负责(GITHUB_TOKEN), 本脚本只改工作区文件。
密钥策略: CI无LLM密钥则自动跳过LLM环节(do_llm=False); 若仓库secrets注入VINF_KEY_*则自动启用。
"""
import os, sys, time, json

WORK = os.path.dirname(os.path.abspath(__file__))
os.environ['VINF_WORK'] = WORK
os.chdir(WORK)
sys.path.insert(0, WORK)

import vinf_console as vc
import vinf_agents as va
from vinf_os import Kernel39
from vinf_finance import FinanceEngine


def main():
    # 0 链完整性门: 断链即失败(红徽章), 由看门狗/人工介入
    v = vc.verify_chain()
    if not v['ok']:
        print('CHAIN_BROKEN:', v['detail']); sys.exit(2)
    print(f"chain ok: {v['hops']} hops, tail={v['tail']}")

    # 1 内核tick (闭包→[resolver/pool缺席CI]→journal)
    k = Kernel39(workdir=WORK)
    acts = k.tick(do_llm=bool(os.environ.get('VINF_KEY_DEEPSEEK')))

    # 2 金融引擎四检
    fin = FinanceEngine(k.db).run_all()
    fsum = [(r['fid'], r['verdict']) for r in fin]
    acts.append(f"finance: {fsum}")
    for r in fin:
        print(f"  [{r['fid']}] {r['verdict']} — {r.get('detail','')}")

    # 3 状态与bundle
    st = vc.status(write=True)
    acts.append(f"status: chain=ok tail={st['chain'].get('tail')}")
    k.journal(acts[1:])          # 第二跳: 金融+状态(首跳closure)
    print(f"journal: {v['hops']+2} hops")

    # 4 重建状态包(Dashboard契约)
    import subprocess
    r = subprocess.run([sys.executable, 'vinf_console.py', 'bundle'],
                       capture_output=True, text=True, cwd=WORK)
    print(r.stdout.strip() or r.stderr[:200])
    print('CI_TICK_OK')


if __name__ == '__main__':
    main()
