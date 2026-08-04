#!/usr/bin/env python3
"""v∞ 推理机 — 细胞复形/知识图谱的自推演·自验证·自涌现
通用/可复用: 输入任意理论库+KG+复形, 输出推理报告+涌现提案。
- 自推演: 前向链规则(传递依赖/派生闭包/状态传播)
- 自验证: 拓扑审计(χ=V-E+F vs β0-β1) + 状态互斥 + 符号引擎交叉验证(sympy可算命题)
- 自涌现: 推理产物(新边候选/矛盾警报/孤儿连接建议)以 raw-need-distill 注入提案池
  —— 涌现物不直接升格, 须过章法R7蒸馏+代码判决(A2/T9)
"""
import json
import os
import sqlite3
import time

WORK = os.path.dirname(os.path.abspath(__file__))


def iri_safe(s, maxlen=40):
    import re as _re
    return _re.sub(r'[^A-Za-z0-9_-]', '-', str(s))[:maxlen] or 'unknown'


class Reasoner:
    def __init__(self, db_path=None, kg_path=None, pool_path=None, bundle_path=None):
        self.db = sqlite3.connect(db_path or os.path.join(WORK, 'theory_db.sqlite'))
        self.kg = json.load(open(kg_path or os.path.join(WORK, 'kg.json')))
        self.pool_path = pool_path or os.path.join(WORK, 'pool.json')
        self.bundle = json.load(open(bundle_path or os.path.join(WORK, 'state_bundle.json')))
        self.report = dict(ts=time.strftime('%Y-%m-%d %H:%M:%S'),
                           deductions=[], topology={}, sympy_xval=[],
                           contradictions=[], emergent=[])

    # ---------- 自推演: 前向链 ----------
    def deduce(self):
        edges = [(iri_safe(e['src']), iri_safe(e['dst']), e['rel']) for e in self.kg['edges']]
        status = {iri_safe(t[0]): t[1] for t in self.db.execute('SELECT id,status FROM theorems')}
        deps = [(s, d) for s, d, r in edges if r == 'dep']
        derived = [(s, d) for s, d, r in edges if r == 'derives']
        # R1 传递依赖闭包(新增边候选, 限增量)
        known = set(deps)
        new_edges = []
        frontier = list(deps)
        for _ in range(3):  # 3轮足够(图小)
            nxt = []
            for a, b in frontier:
                for c, d in deps:
                    if b == c and (a, d) not in known and a != d:
                        known.add((a, d)); new_edges.append((a, d)); nxt.append((a, d))
            frontier = nxt
        for a, d in new_edges[:10]:
            self.report['deductions'].append(f'传递依赖: {a} →dep→ {d}')
        # R2 状态传播: 若A成立且A derives B且B open → B获得"派生支持"提名
        for s, d in derived:
            if status.get(s) in ('established', 'certified', 'proved') and status.get(d) == 'open':
                self.report['deductions'].append(f'状态传播提名: {s}(成立) derives {d}(open) → 建议优先判决 {d}')
        # R3 矛盾扫描: 已证伪者的下游派生物须打污染标记
        refuted = {k for k, v in status.items() if v == 'refuted'}
        for s, d in derived:
            if s in refuted and status.get(d) in ('established', 'certified'):
                self.report['contradictions'].append(f'{s}(证伪) derives {d}(成立) — 基础污染, 须复核')
        return new_edges

    # ---------- 自验证: 拓扑审计 ----------
    def topology_audit(self):
        cc = self.bundle.get('cell_complex', {})
        V, E, F = cc.get('V'), cc.get('E'), cc.get('F')
        b0, b1 = cc.get('betti0'), cc.get('betti1')
        if None in (V, E, F, b0, b1):
            self.report['topology'] = dict(ok=False, note='复形数据缺席')
            return
        chi = V - E + F
        b01 = b0 - b1
        b2_implied = chi - b01  # 2-复形: χ=β0-β1+β2 → β2由审计反解
        ok = b2_implied >= 0
        self.report['topology'] = dict(ok=ok, V=V, E=E, F=F, chi=chi, betti=(b0, b1),
                                       betti2_implied=b2_implied,
                                       note=f'χ={chi}=β0-β1+β2 → β2={b2_implied}(反解)' if ok
                                       else f'χ={chi} < β0-β1={b01} — β2为负, 复形构建矛盾')
        if not ok:
            self.report['contradictions'].append(f'欧拉示性数矛盾: χ={chi} < β0-β1={b01} — 复形构建有洞')

    # ---------- 交叉验证: sympy 可算命题 ----------
    def sympy_xval(self, budget=6):
        """对含纯算术/不等式的命题文本做符号引擎复核(预算制)"""
        import re
        try:
            import sympy as sp
        except ImportError:
            return
        tried = 0
        for tid, stmt, status in self.db.execute(
                "SELECT id,statement,status FROM theorems WHERE status IN ('open','axiom_candidate')"):
            if tried >= budget:
                break
            # 只碰"可机械化"的纯数值断言, 如 '2+2=4' / 'ln2<1'
            m = re.fullmatch(r'\s*([\d\.\+\-\*/\^\(\) ]+)\s*([<>=]+)\s*([\d\.\+\-\*/\^\(\) ]+)\s*', stmt)
            if not m:
                continue
            tried += 1
            try:
                l, r = sp.sympify(m.group(1)), sp.sympify(m.group(3))
                op = m.group(2)
                res = {'=': sp.simplify(l - r) == 0, '==': sp.simplify(l - r) == 0,
                       '<': bool(l < r), '>': bool(l > r),
                       '<=': bool(l <= r), '>=': bool(l >= r)}.get(op)
                self.report['sympy_xval'].append(
                    dict(id=tid, stmt=stmt[:60], verdict=res, engine='sympy',
                         conflict=(res is False and status in ('established', 'certified'))))
            except Exception:
                continue

    # ---------- 自涌现: 提案池注入 ----------
    def emerge(self):
        pool = json.load(open(self.pool_path))
        existing = {p.get('text', '') for p in pool}
        n0 = len(pool)
        cand = []
        for d in self.report['deductions'][:6]:
            cand.append(f'[reasoner] {d}')
        for c in self.report['contradictions'][:4]:
            cand.append(f'[reasoner:ALARM] {c}')
        if self.report['topology'].get('ok') is False:
            cand.append(f"[reasoner:ALARM] 拓扑审计失败 {self.report['topology'].get('note')}")
        for x in self.report['sympy_xval']:
            if x.get('conflict'):
                cand.append(f"[reasoner:sympy] {x['id']} 与符号判决冲突: {x['stmt']}")
        for text in cand:
            if text in existing:
                continue
            pool.append(dict(id=f'R{len(pool):03d}', text=text, parents=[], gen=0,
                             fitness=0.0, novelty=1.0, status='raw-need-distill'))
        self.report['emergent'] = [p['id'] for p in pool[n0:]]
        if len(pool) != n0:
            json.dump(pool, open(self.pool_path, 'w'), ensure_ascii=False, indent=1)
        return len(pool) - n0

    def run(self):
        self.deduce()
        self.topology_audit()
        self.sympy_xval()
        n = self.emerge()
        p = os.path.join(WORK, 'reasoner_report.json')
        json.dump(self.report, open(p, 'w'), ensure_ascii=False, indent=1)
        return p, n


if __name__ == '__main__':
    p, n = Reasoner().run()
    r = json.load(open(p))
    print(f'推演 {len(r["deductions"])} · 矛盾 {len(r["contradictions"])} · sympy复核 {len(r["sympy_xval"])} · 涌现注入 {n}')
    print('拓扑:', r['topology'].get('note'))
    for d in r['deductions'][:6]:
        print(' ', d)
    for c in r['contradictions']:
        print(' !', c)
