#!/usr/bin/env python3
"""v∞ 医官 — 内核自检/自验证/自修复(第54章)
原则: 一切可机械修复的静默修复并留痕; 不可修复的登记台账并如实报告(禁止伪造)。
检查面: 链完整性 / 状态滞后(文件在而status说skip) / 资产陈旧 / 状态包新鲜度 / 推理机审计。
修复面: 重跑status / 重建bundle / iFinD增量刷新(agent-gw可用时) / 本体+推理机重跑。
"""
import json
import os
import subprocess
import sys
import time

WORK = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, WORK)


def _run(script, *args, timeout=600):
    r = subprocess.run([sys.executable, os.path.join(WORK, script), *args],
                       capture_output=True, text=True, timeout=timeout, cwd=WORK)
    return r.returncode, (r.stdout + r.stderr)[-300:]


class Doctor:
    def __init__(self):
        self.rep = dict(ts=time.strftime('%Y-%m-%d %H:%M:%S'), checks=[], repairs=[], open_issues=[])

    def check(self, name, ok, note, repair=None):
        self.rep['checks'].append(dict(name=name, ok=bool(ok), note=note))
        if not ok and repair:
            rc, out = repair()
            self.rep['repairs'].append(dict(name=name, rc=rc, out=out))
            return rc == 0
        return ok

    def run(self):
        # 1 链完整性(不可自修——断链即停, 上报)
        import vinf_console as vc
        v = vc.verify_chain()
        self.check('链完整性', v['ok'], f"{v.get('hops')}跳 尾{v.get('tail')}")
        if not v['ok']:
            self.rep['open_issues'].append('哈希链断裂: 禁止一切写入, 须人工恢复最近一致快照')
            self._save(); return self.rep

        # 2 状态滞后: 文件在而status报skip → 重跑status
        st_path = os.path.join(WORK, 'heartbeat_status.json')
        st = json.load(open(st_path))
        fin = st.get('finance', [])
        stale_skip = any('vrp_ladder.csv缺席' in f for f in fin) and os.path.exists(os.path.join(WORK, 'vrp_ladder.csv'))
        self.check('金融状态新鲜度', not stale_skip,
                   'F1误报skip(文件已在, status滞后)' if stale_skip else 'status与文件一致',
                   repair=lambda: _run('vinf_console.py', 'status'))

        # 3 资产陈旧(CN系可自修: iFinD增量)
        try:
            import pandas as pd
            cn = pd.read_csv(os.path.join(WORK, 'csi300.csv'))
            last = pd.Timestamp(cn.iloc[-1, 0])
            age = (pd.Timestamp.now().normalize() - last).days
            self.check('CN系时效', age <= 4, f'沪深300最新{last.date()} ({age}d)',
                       repair=lambda: _run('vinf_refresh_cn.py'))
        except Exception as e:
            self.check('CN系时效', False, f'读取失败 {e}')

        # 4 状态包新鲜度
        b_path = os.path.join(WORK, 'state_bundle.json')
        b_age_h = (time.time() - os.path.getmtime(b_path)) / 3600
        self.check('状态包新鲜度', b_age_h < 12, f'bundle {b_age_h:.1f}h前',
                   repair=lambda: _run('vinf_console.py', 'bundle'))

        # 5 本体/推理机审计(自验证面)
        rc, out = _run('vinf_ontology.py')
        triples_ok = 'OK' in out
        self.check('本体回读', triples_ok, out.strip().splitlines()[-1] if out else '')
        if not triples_ok:
            self.rep['open_issues'].append('本体导出损坏 — 须人工复核vinf_ontology')
        rc2, out2 = _run('vinf_reasoner.py')
        self.check('推理机', rc2 == 0, out2.strip().splitlines()[0] if out2 else '')

        # 6 不可自修缺口(如实登记)
        mp = json.load(open(os.path.join(WORK, 'market_pulse.json')))
        for k, a in (mp.get('assets') or {}).items():
            if (a.get('stale_days') or 0) > 7:
                self.rep['open_issues'].append(
                    f'{a.get("name", k)}失联{a["stale_days"]}d — 源链Yahoo/FRED/Stooq均不可达处, 台账债#7/#8跟踪')
        self._save()
        return self.rep

    def _save(self):
        json.dump(self.rep, open(os.path.join(WORK, 'doctor_report.json'), 'w'),
                  ensure_ascii=False, indent=1)


if __name__ == '__main__':
    rep = Doctor().run()
    ok = sum(1 for c in rep['checks'] if c['ok'])
    print(f"医官巡检: {ok}/{len(rep['checks'])}项健康 · 修复{len(rep['repairs'])} · 遗留{len(rep['open_issues'])}")
    for c in rep['checks']:
        print(f"  [{'✓' if c['ok'] else '✗'}] {c['name']}: {c['note']}")
    for r in rep['repairs']:
        print(f"  [修] {r['name']} rc={r['rc']}")
    for i in rep['open_issues']:
        print(f"  [遗留] {i}")
