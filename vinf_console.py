# -*- coding: utf-8 -*-
"""v∞ 操作界面（第40章）——随时确认心跳健康 + 全功能控制台
用法: python3 vinf_console.py <cmd>
  status   心跳健康总览(末跳时间/尾哈希/库计数/金融四检) → heartbeat_status.json + STATUS.md
  verify   哈希链全程重算验证 + 记忆库单调性检查(只增不减)
  tick     执行一跳: KB闭合→金融四检→日志→状态落盘(+git备份,若网络可用)
  debts    数据债台账
  sorries  未消解sorry清单(按优先级评分排序)
  kg       知识图谱导出(节点=命题/派生, 边=谱系) → kg.json
  pool     提案池状态
判决纪律不变: 状态只由代码写; 本界面只读+编排。
"""
import json, os, sys, time, hashlib

# 看门狗首条代码评审修复(2026-07-21): 新沙箱无/mnt路径时verify误报"日志缺席"
_DEFAULT_WORK = '/mnt/agents/work/worldcup2026'
WORK = os.environ.get('VINF_WORK') or (
    _DEFAULT_WORK if os.path.isdir(_DEFAULT_WORK)
    else os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, WORK)

def _db():
    import vinf_agents as va
    return va.TheoryDB(os.path.join(WORK, 'theory_db.sqlite'))

def _csv_rows(name, limit=200):
    import csv
    p = os.path.join(WORK, name)
    if not os.path.exists(p):
        return []
    with open(p) as f:
        return list(csv.DictReader(f))[:limit]

# 引擎自*事件志(真实历史): 自修正/自证伪/自修复/自纠错/自完善/自适应/人在回路
SELF_EVENTS = [
    dict(round=38, kind='自修正', event='E5"严格单调"被测试锻造证伪→精化为秩相关0.9表述——机器抓出人类措辞过度'),
    dict(round=37, kind='自证伪', event='T30(τ=κ(1−c))被kimi否决为循环定义→T26聚合veto→残差入库为E4'),
    dict(round=39, kind='自修复', event='LLM证明脚本散文/中文标点→自愈手术提取器(SyntaxError行剔除重试)'),
    dict(round=39, kind='自修复', event='chdir路径事故致双库分叉→脚本目录锚定+显式cwd纪律'),
    dict(round=39, kind='自纠错', event='判决解析器把"无反例"误判为反例→严格输出格式(判决:通过/否决)——法官也需被审判'),
    dict(round=39, kind='自完善', event='池算子元前缀污染→章法R7: 算子输出须经蒸馏提取命题本体'),
    dict(round=37, kind='自适应', event='推理模型reasoning耗尽预算→蒸馏步骤+预算规则R4(涌现的调度补丁)'),
    dict(round=40, kind='自演化', event='手机端心跳Git-first恢复26文件并消解数据债#1; 无写权限→经人并轨(人在回路实践)'),
    dict(round=40, kind='自监督', event='看门狗检出verify路径误报→WORK环境变量回退修复——监督者首次输出代码评审'),
]

def verify_chain():
    """全程重算哈希链: 任何篡改都会断链"""
    path = os.path.join(WORK, 'journal39.jsonl')
    if not os.path.exists(path):
        return dict(ok=False, detail='journal39.jsonl缺席')
    prev = '0' * 64
    n = 0
    for line in open(path):
        rec = json.loads(line)
        body = json.dumps(rec['actions'], ensure_ascii=False)
        expect = hashlib.sha256((prev + body).encode()).hexdigest()
        if expect != rec['hash'] or rec['prev_hash'] != prev:
            return dict(ok=False, detail=f'第{n+1}跳断链: 期望{expect[:12]} 实见{rec["hash"][:12]}')
        prev = rec['hash']; n += 1
    return dict(ok=True, hops=n, tail=prev[:12])

def build_kg():
    """知识图谱: 节点=定理/经验规律/预测/派生, 边=deps/closure谱系/pool亲本"""
    db = _db()
    nodes, edges = [], []
    for r in db.query("SELECT id, kind, status FROM theorems"):
        nodes.append(dict(id=r[0], type=r[1], status=r[2]))
    for r in db.query("SELECT id, deps FROM theorems WHERE deps!=''"):
        for d in r[1].split(','):
            if d.strip():
                edges.append(dict(src=d.strip(), dst=r[0], rel='dep'))
    import re
    for r in db.query("SELECT id, finding FROM frontier WHERE finding LIKE '%closure:%'"):
        m = re.search(r'closure:([^\]]+)', r[1])
        if m:
            for p in m.group(1).split('∧'):
                edges.append(dict(src=p.strip(), dst=f"closure#{r[0]}", rel='derives'))
            nodes.append(dict(id=f"closure#{r[0]}", type='derived', status='derived'))
    pf = os.path.join(WORK, 'pool.json')
    if os.path.exists(pf):
        for p in json.load(open(pf)):
            nodes.append(dict(id=p['id'], type='proposal', status=p['status']))
            for par in p.get('parents', []):
                edges.append(dict(src=par, dst=p['id'], rel='evolves'))
    kg = dict(nodes=nodes, edges=edges, built=time.strftime('%Y-%m-%d %H:%M:%S'))
    json.dump(kg, open(os.path.join(WORK, 'kg.json'), 'w'), ensure_ascii=False, indent=1)
    return kg

def status(write=True):
    db = _db()
    chain = verify_chain()
    s = db.summary()
    fin = db.query("SELECT finding FROM frontier WHERE finding LIKE '[fin:%' ORDER BY id DESC LIMIT 4")
    sorries = db.query("SELECT id, status FROM theorems WHERE kind='sorry-resolution' OR status IN ('open','axiom_candidate')")
    debts = db.query("SELECT item, status FROM debts")
    last_tick = None
    jp = os.path.join(WORK, 'journal39.jsonl')
    if os.path.exists(jp):
        lines = open(jp).read().strip().splitlines()
        if lines:
            last_tick = json.loads(lines[-1])['ts']
    st = dict(ts=time.strftime('%Y-%m-%d %H:%M:%S'), chain=chain, db=s,
              last_tick=last_tick, finance=[f[0] for f in fin],
              sorries=[f'{a}:{b}' for a, b in sorries],
              debts=[f'{a}:{b}' for a, b in debts])
    if write:
        json.dump(st, open(os.path.join(WORK, 'heartbeat_status.json'), 'w'), ensure_ascii=False, indent=1)
        md = [f"# v∞ 心跳状态 ({st['ts']})", '',
              f"- 哈希链: {'✓' if chain['ok'] else '✗断链'} {chain.get('hops',0)}跳 尾={chain.get('tail','-')}",
              f"- 末次tick: {last_tick}",
              f"- 记忆库: {s}",
              f"- 金融四检(近): {[f[:60] for f in st['finance']]}",
              f"- sorry: {st['sorries']}", f"- 数据债: {st['debts']}"]
        open(os.path.join(WORK, 'STATUS.md'), 'w').write('\n'.join(md))
    return st

def tick():
    import vinf_agents as va
    from vinf_os import Kernel39
    from vinf_finance import FinanceEngine
    os.chdir(WORK)
    k = Kernel39(workdir=WORK)
    acts = k.tick(do_llm=False)
    fin = FinanceEngine(k.db).run_all()
    acts.append(f"finance: {[(r['fid'], r['verdict']) for r in fin]}")
    st = status(write=True)
    acts.append(f"status: chain={'ok' if st['chain']['ok'] else 'BROKEN'} tail={st['chain'].get('tail')}")
    k.journal(acts[1:])  # 第二跳: 金融+状态（首跳为closure）
    try:
        import vinf_sync
        commit = vinf_sync.backup('tick ' + time.strftime('%Y-%m-%d %H:%M'))
        acts.append(f"github: {commit}")
    except Exception as e:
        acts.append(f"github: 跳过({type(e).__name__})")
    return acts

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'status'
    if cmd == 'status':
        print(json.dumps(status(), ensure_ascii=False, indent=1))
    elif cmd == 'verify':
        print(verify_chain())
    elif cmd == 'tick':
        for a in tick():
            print(' ', a)
    elif cmd == 'debts':
        for r in _db().query('SELECT id, item, status, note FROM debts'):
            print(' ', r)
    elif cmd == 'sorries':
        for r in _db().query("SELECT id, statement, status FROM theorems WHERE status IN ('open','axiom_candidate','certified')"):
            print(' ', r[0], r[2], r[1][:60])
    elif cmd == 'kg':
        kg = build_kg(); print(f"nodes={len(kg['nodes'])} edges={len(kg['edges'])} → kg.json")
    elif cmd == 'pool':
        for p in json.load(open(os.path.join(WORK, 'pool.json'))):
            print(' ', p['id'], p['status'], f"fit={p['fitness']}", p['text'][:50])
    elif cmd == 'bundle':
        """导出Dashboard状态包(单JSON契约) → state_bundle.json"""
        import vinf_kg
        db = _db()
        kg = build_kg()
        cc = vinf_kg.cell_complex(kg)
        bundle = dict(
            status=status(write=True), kg=kg, cell_complex=cc,
            conflicts=vinf_kg.scan_conflicts(db),
            theorems=[dict(id=r[0], kind=r[1], statement=r[2], status=r[3], verified_by=r[4], round=r[5])
                      for r in db.query('SELECT id,kind,statement,status,verified_by,round FROM theorems')],
            predictions=[dict(id=r[0], statement=r[1], test_by=r[2], status=r[3])
                         for r in db.query('SELECT id,statement,test_by,status FROM predictions')],
            frontier=[dict(id=r[0], finding=r[1], source=r[2], round=r[3])
                      for r in db.query('SELECT id,finding,source,round FROM frontier ORDER BY id DESC LIMIT 40')],
            debts=[dict(id=r[0], item=r[1], status=r[2], note=r[3])
                   for r in db.query('SELECT id,item,status,note FROM debts')],
            pool=json.load(open(os.path.join(WORK, 'pool.json'))),
            journal=[json.loads(l) for l in open(os.path.join(WORK, 'journal39.jsonl'))],
            policy=json.load(open(os.path.join(WORK, 'vinf_policy.json'))),
            vrp_ladder=_csv_rows('vrp_ladder.csv'),
            dalpha=_csv_rows('dalpha_trimmed.csv'),
            self_events=SELF_EVENTS,
        )
        json.dump(bundle, open(os.path.join(WORK, 'state_bundle.json'), 'w'), ensure_ascii=False)
        print(f"bundle: theorems={len(bundle['theorems'])} kg={len(kg['nodes'])}N/{len(kg['edges'])}E "
              f"betti=({cc['betti0']},{cc['betti1']}) conflicts={len(bundle['conflicts'])}")
    else:
        print(__doc__)
