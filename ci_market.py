# -*- coding: utf-8 -*-
"""v∞ CI多市场脉搏 (第48章) — 每交易日两次(亚/美收盘后): 刷新三市数据→态势感知→续链→bundle"""
import os, sys, json, time, hashlib

WORK = os.path.dirname(os.path.abspath(__file__))
os.environ['VINF_WORK'] = WORK
os.chdir(WORK)
sys.path.insert(0, WORK)

import vinf_market
import vinf_paper


def main():
    led, pact = vinf_paper.step()   # 虚拟盘先盯市/调仓
    p = vinf_market.build_pulse()   # 态势感知(含轮动板)
    n_sig = len(p['signals'])
    crit = [s for s in p['signals'] if s['level'] == 'critical']
    lines = open('journal39.jsonl').read().strip().split('\n')
    prev = json.loads(lines[-1])['hash']
    brief = '; '.join(f"{k}={a.get('last', 0):.0f}({a.get('stale_days', '?')}d)"
                      for k, a in p['assets'].items() if a.get('last'))
    actions = [f"market-pulse: {brief}",
               f"paper: NAV={led['nav']:.4f} 持仓={led['positions']} 动作={pact}",
               f"signals: {n_sig}条" + (f" 含critical: {crit[0]['text'][:60]}" if crit else ''),
               f"sources: {p['sources']}"]
    rec = dict(tick=int(time.time()), ts=time.strftime('%Y-%m-%d %H:%M:%S'), actions=actions, prev_hash=prev)
    rec['hash'] = hashlib.sha256((prev + json.dumps(actions, ensure_ascii=False)).encode()).hexdigest()
    open('journal39.jsonl', 'a').write(json.dumps(rec, ensure_ascii=False) + '\n')
    print(f"journal: {len(lines)+1} hops, tail={rec['hash'][:12]}")
    for k, a in p['assets'].items():
        if a.get('last'):
            print(f"  {k}: {a['last']:.2f} rv%={a.get('rv_pct3y')} stale={a['stale_days']}d [{a['source']}]")
    print('CI_MARKET_OK')


if __name__ == '__main__':
    main()
