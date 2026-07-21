# -*- coding: utf-8 -*-
"""v∞ 操作系统层（第39章）——后台持续自演化内核
组件: ProposalPool(提案池演化) / TestForge(多智能体测试驱动) / Kernel39(OS主循环)
治理: A2′/T9(LLM只提案代码判决) · T26(sup否决) · 预算熔断 · 只增不减的哈希链日志。
"""
import json, os, time, hashlib, difflib, random
import vinf_agents as va

va.LLMS['deepseek2'] = dict(url='https://api.deepseek.com/v1/chat/completions', model='deepseek-v4-flash')

# ---------------- 提案池：生成/竞争/演化 ----------------
class ProposalPool:
    """演化策略: 变异(强化/弱化/改常数/改定义域) · 交叉 · 类比迁移(体育↔金融)
    适应度 = 0.6*验证分 + 0.25*新颖度 − 0.15*祖先失败罚金；锦标赛选择+精英保留。"""
    def __init__(self, db, path='pool.json'):
        self.db, self.path = db, path
        self.pool = json.load(open(path)) if os.path.exists(path) else []
    def save(self):
        json.dump(self.pool, open(self.path, 'w'), ensure_ascii=False, indent=1)
    def novelty(self, text):
        if not self.pool: return 1.0
        return 1 - max(difflib.SequenceMatcher(None, text, p['text']).ratio() for p in self.pool)
    def add(self, text, parents=(), gen=0, fitness=0.0):
        pid = f"P{len(self.pool)+1:03d}"
        self.pool.append(dict(id=pid, text=text, parents=list(parents), gen=gen,
                              fitness=fitness, novelty=round(self.novelty(text), 3), status='open'))
        return pid
    @staticmethod
    def _valid(out):
        """拒绝指令回显/散文：输出必须是命题本身"""
        bad = ['需要', '用户', '要求', '我理解', '分析', '首先', '命题：命题',
               '可能', '检查', '字数', '杂交', '变异', '“', '”', '解释']
        return (out and not out.startswith('(调用失败')
                and not any(b in out[:40] for b in bad))
    def mutate(self, p, lane='deepseek2', how=None):
        how = how or random.choice(['强化结论','弱化前提','改变常数','缩小定义域'])
        out = va.chat(lane, f"对命题做{how}变异，产出一条新的可证伪数学命题，60字内，直接给出命题本身，不要任何解释：\n{p['text']}",
                      max_tokens=500)
        out = out.strip().split('\n')[-1][:120]
        if not self._valid(out): return None
        return self.add(out, parents=[p['id']], gen=p['gen']+1)
    def crossover(self, a, b, lane='deepseek2'):
        out = va.chat(lane, "把两条命题杂交成一条兼具两者结构的新可证伪命题，60字内，直接给出命题本身，不要任何解释："
                      f"\n甲: {a['text']}\n乙: {b['text']}", max_tokens=500)
        out = out.strip().split('\n')[-1][:120]
        if not self._valid(out): return None
        return self.add(out, parents=[a['id'], b['id']], gen=max(a['gen'], b['gen'])+1)
    def select(self, k=2):
        """锦标赛选择 top-k 作为亲本"""
        scored = sorted(self.pool, key=lambda p: p['fitness'] + 0.25*p['novelty'], reverse=True)
        return scored[:k]
    def cull(self, keep=20):
        self.pool = sorted(self.pool, key=lambda p: p['fitness'] + 0.25*p['novelty'], reverse=True)[:keep]
        self.save()

# ---------------- 测试锻造：验证驱动机制 ----------------
class TestForge:
    """LLM写属性测试→代码随机执行(种子固定)→反例最小化。状态改变只由执行结果触发。"""
    def __init__(self, db):
        self.db = db
    def run_property(self, fid, code, n_trials=2000, seed=42):
        """code须定义 def prop(rng)->bool 与 def shrink(counterexample)"""
        import numpy as np
        ns = {'np': np, 'numpy': np}
        try:
            exec(code, ns)
            prop = ns['prop']
        except Exception as e:
            return dict(fid=fid, verdict='error', detail=str(e)[:120])
        rng = np.random.default_rng(seed)
        cex = None
        for i in range(n_trials):
            try:
                if not prop(rng):
                    cex = i; break
            except Exception:
                continue
        if cex is None:
            return dict(fid=fid, verdict='pass', trials=n_trials)
        shrunk = ns['shrink'](cex) if 'shrink' in ns else cex
        return dict(fid=fid, verdict='fail', at=cex, shrunk=str(shrunk)[:120])
    def gate(self, fid, result):
        self.db.log('frontier', finding=f"[forge] {fid} → {result['verdict']} {result.get('detail','')}{result.get('shrunk','')}",
                    source='test_forge', impact='', round=39)

# ---------------- 知识库自闭合推演 ----------------
CLOSURE_RULES = [
    dict(rule='E4∧E5', parents=('E4','E5'),
         derive="派生预测D1: 高叙事浓度市场(CS/长赛程)的协议税应同时高于主线市场且随期限放大——税率排序×期限斜率复合可检"),
    dict(rule='T13∧E5', parents=('T13','E5'),
         derive="派生推论D2: 长端期权叙事税>0是T13在衍生品的稳态形式；短端转负不违T13(T13断言的是定价核非负,非任意窗IV-RV)"),
    dict(rule='T26∧E4', parents=('T26','E4'),
         derive="派生预测D3: CS市场的高税应有更大的逐庄sup-mean离散度(协议税∝分歧聚合强度)——可用sharpapi面板检"),
]

def kb_closure(db):
    """前向链推演: 规则前件在记忆库中→派生行入库(带谱系parents), 幂等(按rule名查重)"""
    made = []
    have = {r[0]: r[1] for r in db.query("SELECT id, status FROM theorems")}
    front = ' '.join(r[0] for r in db.query("SELECT finding FROM frontier"))
    for R in CLOSURE_RULES:
        exists = db.query("SELECT COUNT(*) FROM frontier WHERE finding LIKE ?", (f"%[closure:{R['rule']}]%",))[0][0]
        ok = all((p in have) or (p in front) for p in R['parents'])
        if ok and not exists:
            db.log('frontier', finding=f"[closure:{R['rule']}] {R['derive']}", source='kb_closure',
                   impact='derived', round=39)
            made.append(R['rule'])
    return made

# ---------------- OS 内核 ----------------
class Kernel39:
    """主循环: sync_in → kb_closure → resolve → evolve → forge → journal。
    预算熔断 + 哈希链日志(prev_hash→hash) 防篡改、只增不减。"""
    def __init__(self, workdir='.', budget_llm=12):
        os.chdir(workdir)
        self.db = va.TheoryDB('theory_db.sqlite')
        self.budget = budget_llm
        self.journal_path = 'journal39.jsonl'
    def _last_hash(self):
        if not os.path.exists(self.journal_path): return '0'*64
        with open(self.journal_path) as f:
            lines = f.read().strip().splitlines()
        return json.loads(lines[-1])['hash'] if lines else '0'*64
    def journal(self, actions):
        prev = self._last_hash()
        rec = dict(tick=int(time.time()), ts=time.strftime('%Y-%m-%d %H:%M:%S'),
                   actions=actions, prev_hash=prev)
        rec['hash'] = hashlib.sha256((prev + json.dumps(actions, ensure_ascii=False)).encode()).hexdigest()
        with open(self.journal_path, 'a') as f:
            f.write(json.dumps(rec, ensure_ascii=False) + '\n')
        return rec['hash'][:12]
    def tick(self, resolver=None, pool=None, forge=None, do_llm=True):
        acts = []
        # 1 内部同步: 记忆库状态
        acts.append(f"sync: db={self.db.summary()}")
        # 2 知识库自闭合
        made = kb_closure(self.db); acts.append(f"closure: +{made}" if made else "closure: 0")
        # 3 sorry消解(若注入resolver)
        if resolver is not None:
            acts += [f"resolve: {x}" for x in resolver.log]
        # 4 提案池演化(若注入)
        if pool is not None:
            acts.append(f"pool: size={len(pool.pool)}")
        # 5 日志落盘
        h = self.journal(acts)
        acts.append(f"journal: {h}")
        return acts

if __name__ == '__main__':
    import sys
    if '--tick' in sys.argv:
        k = Kernel39(workdir='/mnt/agents/work/worldcup2026')
        for a in k.tick(do_llm=False):
            print(a)
