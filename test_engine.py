#!/usr/bin/env python3
"""v∞ 引擎自测试套件 — 每次push/每日自动跑(第55章)
十项契约测试: 任何一项fail即红徽章。全部代码判决, 无LLM印象。
"""
import json
import os
import subprocess
import sys

WORK = os.path.dirname(os.path.abspath(__file__))
os.chdir(WORK)
sys.path.insert(0, WORK)

RESULTS = []


def T(name, fn):
    try:
        ok, note = fn()
    except Exception as e:
        ok, note = False, f'{type(e).__name__}: {str(e)[:80]}'
    RESULTS.append(dict(name=name, ok=bool(ok), note=note))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {note}")


def t_chain():
    import vinf_console as vc
    v = vc.verify_chain()
    return v['ok'], f"{v.get('hops')}跳 尾{v.get('tail')} {v.get('detail','')}"


def t_journal_tail_fresh():
    lines = open('journal39.jsonl').read().strip().splitlines()
    last = json.loads(lines[-1])
    return len(lines) >= 30 and len(last['hash']) == 64, f"{len(lines)}跳"


def t_bundle_contract():
    b = json.load(open('state_bundle.json'))
    need = ['status', 'kg', 'cell_complex', 'theorems', 'journal', 'strategies', 'market']
    miss = [k for k in need if k not in b]
    chain_ok = b['status']['chain']['ok']
    return not miss and chain_ok, f"缺{miss or '无'} chain={chain_ok}"


def t_ontology_parse():
    import vinf_ontology
    _, a = vinf_ontology.OntologyExporter().run('/tmp/test_kg.ttl')
    return a['parse_ok'] and a['triples'] > 100, f"三元组{a['triples']} parse={a['parse_ok']}"


def t_reasoner():
    import vinf_reasoner
    p, _ = vinf_reasoner.Reasoner().run()
    r = json.load(open(p))
    topo = r['topology'].get('ok', False)
    return topo, r['topology'].get('note', '')


def t_finance_checks():
    import vinf_console as vc
    import vinf_finance
    rs = vinf_finance.FinanceEngine(vc._db()).run_all()
    bad = [r['fid'] for r in rs if r['verdict'] not in ('pass', 'archived')]
    return not bad, ';'.join(f"{r['fid']}:{r['verdict']}" for r in rs)


def t_doctor():
    import vinf_doctor
    rep = vinf_doctor.Doctor().run()
    crit_fail = [c for c in rep['checks'] if not c['ok'] and c['name'] in ('链完整性', '金融状态新鲜度')]
    return not crit_fail, f"{sum(1 for c in rep['checks'] if c['ok'])}/{len(rep['checks'])}健康 修复{len(rep['repairs'])}"


def t_command_registry():
    import vinf_commands
    known = {'REFRESH-CN', 'REFRESH-CN-FULL', 'FIN-STATUS', 'DOCTOR', 'BUNDLE', 'ONTOLOGY'}
    missing = known - set(vinf_commands.COMMANDS)
    bad = vinf_commands.execute('__NOPE__')
    return not missing and bad['rc'] == 127, f"注册{len(vinf_commands.COMMANDS)}个 未知命令拒绝rc={bad['rc']}"


def t_engine_facade():
    import engine
    e = engine.Engine(WORK)
    info = e.info()
    return info['chain']['ok'] and info['version'] >= '2.6.0', f"v{info['version']} chain=ok"


def t_data_freshness_cn():
    import pandas as pd
    last = pd.Timestamp(pd.read_csv('csi300.csv').iloc[-1, 0])
    age = (pd.Timestamp.now().normalize() - last).days
    return age <= 7, f"沪深300最新{last.date()} ({age}d)"


def main():
    print('== v∞ 引擎自测试 ==')
    for name, fn in list(globals().items()):
        if name.startswith('t_'):
            T(name[2:], fn)
    nok = sum(1 for r in RESULTS if r['ok'])
    print(f'== {nok}/{len(RESULTS)} PASS ==')
    json.dump(dict(ts=__import__('time').strftime('%Y-%m-%d %H:%M:%S'), results=RESULTS),
              open('selftest_report.json', 'w'), ensure_ascii=False, indent=1)
    sys.exit(0 if nok == len(RESULTS) else 1)


if __name__ == '__main__':
    main()
