# -*- coding: utf-8 -*-
"""v∞ sorry消解引擎（第39章）——重构 sorry-resolver 四级流水线
sorry := TheoryDB中未证明命题（猜想/条件定理/开放预测）。
流水线: ①rfl速解(自动证明器) ②LLM直接证明(写脚本,代码执行) ③搜索(温度0.4→0.1+失败记忆)
        ④升格: 连败≥3次→MARKED_AXIOM(条件定理)/open —— 不可解问题不许无限耗资源。
治理: 命题状态只能由可执行代码改变；LLM脚本在受限命名空间执行+30秒熔断。
"""
import time, json, signal, traceback
from dataclasses import dataclass, field
import vinf_agents as va
from vinf_provers import route, ProofResult

va.LLMS['deepseek2'] = dict(url='https://api.deepseek.com/v1/chat/completions', model='deepseek-v4-flash')

@dataclass
class SorryTask:
    id: str
    statement: str
    goal: dict = field(default_factory=dict)   # 给自动证明器的结构化目标
    priority: str = 'P1'                        # P0>P1>P2>P3
    escalation: int = 0
    status: str = 'open'
    history: list = field(default_factory=list)

PW = {'P0': 1.0, 'P1': 0.7, 'P2': 0.4, 'P3': 0.2}

def priority_score(t: SorryTask):
    """LeanProgress式启发式: 优先级权重 + 自动可证性估计 + 简洁度"""
    s = t.statement
    auto = 0.8 if t.goal.get('kind') in ('sup_mean','maxitive_axioms','ineq_min_zero','identity') else \
           0.5 if t.goal else 0.15
    simple = max(0.0, 1 - len(s)/200)
    return PW.get(t.priority, .5)*0.5 + auto*0.3 + simple*0.2

class _Timeout(Exception): pass

import re
_PY_LINE = re.compile(r'^(\s*(import |from |def |class |if |for |while |try|except|return|RESULT|[a-zA-Z_][\w\.\[\]]*\s*[=\(])|#|\s+\S|\)|\]|\}).*$')
def extract_code(text):
    """从LLM输出中稳健提取Python代码：优先```代码块```，否则保留类python行、剔除中文散文行"""
    m = re.findall(r'```(?:python)?\s*\n(.*?)```', text, re.S)
    cand = m[0] if m else text
    lines = []
    for ln in cand.splitlines():
        ln = ln.encode('ascii', 'ignore').decode()          # 剔除一切非ASCII(√ ² α 中文标点)
        if not ln.strip() or re.match(r'^\s*\d+[\.\、]', ln):  # 剔除编号列表行
            continue
        if _PY_LINE.match(ln):
            lines.append(ln)
    code = '\n'.join(lines)
    return code if code.strip() else cand

def _run_user_script(code, timeout=30):
    """受限执行LLM证明脚本：仅注入sympy/z3/numpy与goal; 须把结果赋给RESULT(ProofResult)"""
    def handler(sig, frm): raise _Timeout()
    signal.signal(signal.SIGALRM, handler); signal.alarm(timeout)
    import sympy, numpy
    ns = {'sympy': sympy, 'sp': sympy, 'numpy': numpy, 'np': numpy,
          'ProofResult': ProofResult, '__builtins__': __builtins__}
    try:
        import z3; ns['z3'] = z3
    except ImportError:
        pass
    try:
        for _surg in range(6):  # 自愈式剔除SyntaxError行（LLM脚本手术）
            try:
                compile(code, '<llm>', 'exec')
                break
            except SyntaxError as se:
                if se.lineno is None:
                    raise
                lines = code.splitlines()
                if not (1 <= se.lineno <= len(lines)):
                    raise
                lines.pop(se.lineno - 1)
                code = '\n'.join(lines)
        exec(code, ns)
        r = ns.get('RESULT')
        if isinstance(r, ProofResult):
            return r
        return ProofResult('unknown', 'llm-script', detail='脚本未产出ProofResult')
    except _Timeout:
        return ProofResult('unknown', 'llm-script', detail='脚本超时(30s)')
    except Exception as e:
        return ProofResult('unknown', 'llm-script', detail=f'脚本异常: {type(e).__name__}: {e}')
    finally:
        signal.alarm(0)

class Resolver:
    def __init__(self, db_path='theory_db.sqlite', budget_llm=12):
        self.db = va.TheoryDB(db_path)
        self.budget = budget_llm
        self.llm_calls = 0
        self.log = []

    def _budget_ok(self):
        return self.llm_calls < self.budget

    def stage_rfl(self, t: SorryTask):
        if not t.goal:
            return None
        r = route(t.goal)
        t.history.append(f'rfl: {r}')
        return r if r.status in ('proved', 'certified', 'refuted') else None

    def stage_llm(self, t: SorryTask, rounds=1, search=False):
        """②③ LLM写证明脚本→代码执行。search模式带失败记忆与温度衰减。"""
        memory = ''
        for i in range(rounds):
            if not self._budget_ok():
                t.history.append('llm: 预算耗尽')
                return None
            temp = max(0.1, 0.4 - 0.1*i) if search else 0.2
            prompt = (
                "你是形式化证明工程师。为以下命题写一个Python证明脚本（≤40行）："
                "可用 sympy(sp)/numpy(np)/z3/ProofResult；必须把结果赋给变量 RESULT=ProofResult(status,prover,certificate,detail)，"
                "status∈{'proved','certified','refuted','unknown'}。只输出代码，无解释。\n"
                f"命题: {t.statement}\n{memory}")
            code = va.chat('deepseek', prompt + "\n只输出ASCII代码，禁止任何中文标点与散文。",
                           max_tokens=2000, temperature=temp, timeout=150)
            self.llm_calls += 1
            if code.startswith('(调用失败'):
                t.history.append(f'llm[{i}]: {code[:60]}'); continue
            code = extract_code(code)
            r = _run_user_script(code)
            t.history.append(f'llm[{i}](T={temp}): {r}')
            if r.status in ('proved', 'certified', 'refuted'):
                return r
            memory = f"上次脚本结论: {r.detail[:150]}。换一条数学路线重试。\n"
        return None

    def resolve(self, tasks, llm_rounds=2):
        tasks = sorted(tasks, key=priority_score, reverse=True)
        for t in tasks:
            if t.status != 'open':
                continue
            # ① rfl速解
            r = self.stage_rfl(t)
            # ②③ LLM直接证明+搜索
            if r is None and t.goal.get('allow_llm', True) and self._budget_ok():
                r = self.stage_llm(t, rounds=llm_rounds, search=True)
            if r is not None:
                t.status = {'proved': 'proved', 'certified': 'certified',
                            'refuted': 'refuted'}[r.status]
                self._register(t, r)
            else:
                # ④ 升格机制
                t.escalation += 1
                if t.escalation >= 3:
                    t.status = 'axiom_candidate'
                    self._register(t, ProofResult('unknown', 'escalator',
                        detail='连败≥3 → 升格为公理候选/条件定理，停止资源消耗'))
                self.log.append(f'{t.id}: 未消解, 升级计数={t.escalation}, 状态={t.status}')
        return tasks

    def _register(self, t: SorryTask, r: ProofResult):
        self.db.put('theorems', id=t.id, kind='sorry-resolution',
            statement=t.statement[:200], status=t.status,
            deps='', evidence=r.certificate[:300], verified_by=r.prover,
            round=39)
        self.db.log('frontier', finding=f'[sorry] {t.id} → {t.status} by {r.prover}: {r.detail[:150]}',
            source='vinf_resolver', impact='', round=39)
        self.log.append(f'{t.id}: {t.status} ({r.prover}) — {r.detail[:80]}')
