# -*- coding: utf-8 -*-
"""v39 全流程实跑：sorry消解 + 提案池演化 + 测试锻造 + flash/pro证伪基准 + OS tick"""
import sys, os, json, time
os.chdir('/mnt/agents/work/worldcup2026')
sys.path.insert(0, '/mnt/agents/work/worldcup2026')
import vinf_agents as va
va.LLMS['deepseek2'] = dict(url='https://api.deepseek.com/v1/chat/completions', model='deepseek-v4-flash')
from vinf_resolver import SorryTask, Resolver, priority_score
from vinf_os import ProposalPool, TestForge, Kernel39

STAGE = sys.argv[1] if len(sys.argv) > 1 else 'rfl'

TASKS = [
    SorryTask('T1', 'T1: 任意非负权重w(和为1)与实数x_i，加权均值Σw_i x_i ≤ max(x)',
        goal={'kind': 'sup_mean', 'provers': ['z3']}, priority='P0'),
    SorryTask('AX-MAX', 'maxitive代数四公理：幂等max(x,x)=x、交换、结合、单调(x≤y⟹max(x,z)≤max(y,z))',
        goal={'kind': 'maxitive_axioms', 'provers': ['z3']}, priority='P0'),
    SorryTask('GIBBS-2', 'Gibbs不等式(二点分布)：D(p||q)=p·ln(p/q)+(1−p)·ln((1−p)/(1−q)) ≥ 0 (q=0.3固定)',
        goal={'kind': 'ineq_min_zero', 'var': 'p', 'expr': 'p*log(p/0.3)+(1-p)*log((1-p)/0.7)',
              'min_at': '0.3', 'provers': ['sympy']}, priority='P0'),
    SorryTask('RENYI-MONO', '同均值高斯q=N(0,s²),p=N(0,t²)(s≠t)的Rényi散度D_α(q||p)关于α>0严格递增',
        goal={'kind': 'llm_only', 'allow_llm': True}, priority='P1'),
    SorryTask('T29', 'T29(条件定理): 市场时间晶体结构=热带半环上的循环性(sup-卷积谱的周期点)',
        goal={'kind': 'llm_only', 'allow_llm': True}, priority='P2', escalation=2),
]

if STAGE in ('rfl', 'all'):
    print('=== ① rfl速解层（z3/sympy自动证明器）===')
    rz = Resolver(budget_llm=0)
    for t in TASKS[:3]:
        print(f'  {t.id} score={priority_score(t):.2f}')
    out = rz.resolve(TASKS[:3])
    for t in out:
        print(f'  → {t.id}: {t.status} | {t.history[-1][:120]}')
    print('  db:', rz.db.summary())

if STAGE in ('llm', 'all'):
    print('\n=== ②③④ LLM证明搜索层 + 升格机制 ===')
    rz = Resolver(budget_llm=5)
    out = rz.resolve(TASKS[3:], llm_rounds=2)
    for t in out:
        print(f'  → {t.id}: {t.status} (esc={t.escalation})')
        for h in t.history[-3:]:
            print(f'      {h[:150]}')
    print('  LLM调用:', rz.llm_calls)

if STAGE in ('pool', 'all'):
    print('\n=== 提案池演化 ===')
    db = va.TheoryDB('theory_db.sqlite')
    pool = ProposalPool(db)
    if not pool.pool:
        pool.add('叙事税沿期权期限单调递增(E5)', gen=0)
        pool.add('协议税∝叙事浓度(E4: CS≫1X2≈O/U)', gen=0)
    parents = pool.select(k=2)
    print('  亲本:', [p['id'] for p in parents])
    m = pool.mutate(parents[0], lane='deepseek')
    c = pool.crossover(parents[0], parents[1], lane='deepseek')
    for p in pool.pool[-2:]:
        print(f"  +{p['id']}(gen{p['gen']},novel{p['novelty']}): {p['text'][:70]}")
    pool.save()

if STAGE in ('forge', 'all'):
    print('\n=== 测试锻造（代码判决）===')
    db = va.TheoryDB('theory_db.sqlite')
    forge = TestForge(db)
    # F1: E5单调性——数据驱动判决(vrp_ladder.csv)
    import pandas as pd
    v = pd.read_csv('vrp_ladder.csv').sort_values('DTE')
    mono = v.VRP_post.is_monotonic_increasing
    r1 = dict(fid='E5-monotone', verdict='pass' if mono else 'fail',
              detail=f"VRP_post序列={[round(x,3) for x in v.VRP_post]}")
    forge.gate('E5-monotone', r1); print(' ', r1)
    # F2: T1随机属性测试(sup≥mean, 2000 trial)
    code = '''
def prop(rng):
    x = rng.normal(size=rng.integers(2, 9))
    w = rng.random(len(x)); w /= w.sum()
    return (w * x).sum() <= x.max() + 1e-12
'''
    r2 = forge.run_property('T1-sup-mean', code)
    forge.gate('T1-sup-mean', r2); print(' ', r2)
    # F3: max-mean聚合方向(T26)随机属性
    code3 = '''
def prop(rng):
    ps = rng.random(rng.integers(2, 7)) * 0.9 + 0.05
    return ps.max() >= ps.mean()
'''
    r3 = forge.run_property('T26-direction', code3)
    forge.gate('T26-direction', r3); print(' ', r3)

if STAGE in ('bench', 'all'):
    print('\n=== flash vs pro vs kimi 证伪基准（章法证据）===')
    FLAWED = ("定理：市场的协议税τ等于叙事浓度c与单位吸收率κ的乘积τ=κ·c，"
              "其中叙事浓度c定义为单位κ下测得的协议税。请审查：若循环论证/隐藏假设/反例请否决；否则通过。"
              "最后一行必须严格输出：判决：通过 或 判决：否决")
    VALID = ("定理：对任意非负权重w_i(和为1)与实数x_i，Σw_i·x_i ≤ max(x_i)。"
             "请审查：若有反例或漏洞请否决；否则通过。最后一行必须严格输出：判决：通过 或 判决：否决")
    for name, lane in [('flash', 'deepseek2'), ('pro', 'deepseek'), ('kimi', 'kimi')]:
        for tag, stmt in [('FLAWED', FLAWED), ('VALID', VALID)]:
            v = va.chat(lane, stmt, max_tokens=1000, timeout=150)
            tail = v[-60:]
            kills = ('判决：否决' in tail) or ('判决:否决' in tail)
            passed = ('判决：通过' in tail) or ('判决:通过' in tail)
            verdict = '否决' if kills else ('通过' if passed else '未决')
            print(f'  {name:6s} {tag:7s}: {verdict} | {v[:70].replace(chr(10)," ")}')

if STAGE in ('tick', 'all'):
    print('\n=== OS tick（闭合并推演+日志链）===')
    k = Kernel39(workdir='.')
    for a in k.tick(do_llm=False):
        print(' ', a)
