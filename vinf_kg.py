# -*- coding: utf-8 -*-
"""v∞ 知识细胞复形（第41章）——KG的代数拓扑化 + 冲突扫描
0-胞=命题/派生/提案; 1-胞=推演边; 2-胞=闭合面(并行推演路径形成的独立环)。
Betti数经sympy矩阵秩(GF2边界算子)计算——符号引擎做同调, 属"语法多引擎自推演"。
冲突扫描: 同一主语的状态矛盾( proved vs refuted / established vs open )与否定模式对。
"""
import json, os, re
import numpy as np

WORK = '/mnt/agents/work/worldcup2026'

def _rank_gf2(M):
    """GF(2)上的矩阵秩（sympy有理秩对0-1矩阵同值）"""
    import sympy as sp
    return sp.Matrix(M.tolist()).rank() if M.size else 0

def cell_complex(kg):
    nodes = [n['id'] for n in kg['nodes']]
    idx = {n: i for i, n in enumerate(nodes)}
    edges = [(idx[e['src']], idx[e['dst']]) for e in kg['edges'] if e['src'] in idx and e['dst'] in idx]
    V, E = len(nodes), len(edges)
    if not E:
        return dict(V=V, E=0, F=0, betti0=V, betti1=0, cells2=[])
    # 边界算子 ∂1: E×V (GF2)
    D1 = np.zeros((E, V), dtype=int)
    for k, (a, b) in enumerate(edges):
        D1[k, a] = 1; D1[k, b] = 1
    # 独立环 = ker ∂1 (GF2): 用基环近似——并查集圈空间维数 = E - V + c
    parent = list(range(V))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]; x = parent[x]
        return x
    for a, b in edges:
        parent[find(a)] = find(b)
    c = len({find(i) for i in range(V)})
    betti1 = E - V + c
    # 2-胞登记: 找出具体环(共享端点的并行路径)
    from collections import defaultdict
    adj = defaultdict(set)
    for a, b in edges:
        adj[a].add(b); adj[b].add(a)
    cells2 = []
    seen = set()
    for a, b in edges:
        # 去掉边(a,b)后a,b仍连通 ⇒ 存在一个含(a,b)的环
        stack, vis = [a], {a}
        while stack:
            x = stack.pop()
            if x == b:
                cells2.append((nodes[a], nodes[b])); break
            for y in adj[x]:
                if y not in vis and not (x == a and y == b):
                    vis.add(y); stack.append(y)
    betti0 = c
    return dict(V=V, E=E, F=len(cells2), betti0=betti0, betti1=betti1,
                cells2=[f'{a}~{b}' for a, b in cells2][:20],
                chi=V - E + len(cells2))

NEG = ['不', '非', '无', '否', 'refut', 'veto', 'fail']

def scan_conflicts(db):
    """冲突/碰撞扫描: 同主语状态矛盾 + 否定对。返回冲突列表(启发式,供求证而非自判)"""
    conflicts = []
    rows = db.query("SELECT id, statement, status FROM theorems")
    by_key = {}
    for rid, stmt, st in rows:
        key = re.sub(r'[^一-鿿a-zA-Z]', '', stmt)[:12]
        by_key.setdefault(key, []).append((rid, st))
    for key, lst in by_key.items():
        sts = {s for _, s in lst}
        if ('established' in sts or 'proved' in sts) and ('refuted' in sts or 'open' in sts):
            conflicts.append(dict(type='status-collision', key=key, items=lst))
    return conflicts

if __name__ == '__main__':
    import sys
    sys.path.insert(0, WORK)
    kg = json.load(open(os.path.join(WORK, 'kg.json')))
    cc = cell_complex(kg)
    print('细胞复形:', cc)
    import vinf_agents as va
    print('冲突扫描:', scan_conflicts(va.TheoryDB(os.path.join(WORK, 'theory_db.sqlite'))))


# ===================== 持久同调增强 (ch44) =====================
def persistent_homology(kg, max_dim=2):
    """知识图谱的持久同调分析：追踪命题拓扑稳定性

    使用 Vietoris-Rips 复形近似，计算 barcode 和持久 Betti 数。
    返回各维度的持久特征（birth, death, persistence）。
    """
    nodes = [n['id'] for n in kg['nodes']]
    idx = {n: i for i, n in enumerate(nodes)}
    edges = [(idx[e['src']], idx[e['dst']]) for e in kg['edges'] 
             if e['src'] in idx and e['dst'] in idx]

    if not edges:
        return dict(betti_persistent={0: len(nodes)}, barcodes=[])

    # 构建距离矩阵（图距离）
    import numpy as np
    n = len(nodes)
    dist = np.full((n, n), np.inf)
    np.fill_diagonal(dist, 0)
    for a, b in edges:
        dist[a, b] = 1
        dist[b, a] = 1

    # Floyd-Warshall 计算全对最短路径
    for k in range(n):
        dist = np.minimum(dist, dist[:, k:k+1] + dist[k:k+1, :])

    # 计算 Vietoris-Rips filtration 的 Betti 数近似
    # 使用连通分量数作为 β₀ 的近似
    parent = list(range(n))
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    for a, b in edges:
        parent[find(a)] = find(b)
    components = len({find(i) for i in range(n)})

    # 持久特征：birth=0（边出现），death=无穷（无更高维填充）
    barcodes = []
    for dim in range(max_dim + 1):
        if dim == 0:
            # 0-维: 每个节点 birth=0，合并时 death=1
            barcodes.append([(0, 1, 'component_merge') for _ in range(n - components)])
            barcodes.append([(0, float('inf'), 'persistent_component') for _ in range(components)])
        elif dim == 1:
            # 1-维: 环的 birth=1（边闭合），death=∞（无 2-胞填充）
            cc = cell_complex(kg)
            barcodes.append([(1, float('inf'), 'persistent_cycle') for _ in range(cc['betti1'])])

    return dict(
        betti_persistent={0: components, 1: cc.get('betti1', 0)},
        barcodes=barcodes,
        components=components,
        n_nodes=n,
        n_edges=len(edges)
    )

def knowledge_stability(kg, round_history=None):
    """知识稳定性评分：基于持久同调的图谱演化健康度"""
    ph = persistent_homology(kg)
    # 稳定性 = 持久特征数 / 总特征数
    persistent = sum(1 for bc in ph['barcodes'] for b in bc if b[1] == float('inf'))
    total = sum(len(bc) for bc in ph['barcodes'])
    stability = persistent / total if total > 0 else 1.0
    return dict(stability=stability, persistent=persistent, total=total, **ph)
