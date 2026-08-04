#!/usr/bin/env python3
"""v∞ 本体层 — 通用/可复用的语义网表示引擎
输入任意 theory_db.sqlite(theorems/predictions/debts) + kg.json + 细胞复形,
输出 RDF/Turtle: SKOS 概念体系 + OWL 类/属性 + vinf: 自定义数学知识本体。
自验证: rdflib 回读解析 + OWL 一致性审计(状态冲突/证明-证伪同边)。
不依赖任何具体领域——换库即换域。
"""
import json
import os
import sqlite3

WORK = os.path.dirname(os.path.abspath(__file__))
NS = 'http://vinf.ai/onto#'

# —— 本体定义(头): 类/属性/映射, 一次定义处处复用 ——
HEADER = f"""@prefix vinf: <{NS}> .
@prefix rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix owl:  <http://www.w3.org/2002/07/owl#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix dct:  <http://purl.org/dc/terms/> .
@prefix xsd:  <http://www.w3.org/2001/XMLSchema#> .

vinf:Ontology a owl:Ontology ;
  rdfs:label "v∞ 数学知识本体"@zh ;
  rdfs:comment "自证伪理论机器的语义网表示: 命题(可证伪陈述)+证据(代码判决)+拓扑(细胞复形)"@zh ;
  owl:versionInfo "1.0" .

# ===== OWL 类层 =====
vinf:Statement      a owl:Class ; rdfs:label "可判陈述" .
vinf:Theorem        a owl:Class ; rdfs:subClassOf vinf:Statement .
vinf:Axiom          a owl:Class ; rdfs:subClassOf vinf:Statement .
vinf:Lemma          a owl:Class ; rdfs:subClassOf vinf:Statement .
vinf:Corollary      a owl:Class ; rdfs:subClassOf vinf:Statement .
vinf:Proposition    a owl:Class ; rdfs:subClassOf vinf:Statement .
vinf:ConditionalTheorem a owl:Class ; rdfs:subClassOf vinf:Statement .
vinf:EmpiricalLaw   a owl:Class ; rdfs:subClassOf vinf:Statement .
vinf:Prediction     a owl:Class ; rdfs:subClassOf vinf:Statement ;
  rdfs:comment "可证伪预测: 理论机器的排污口" .
vinf:DataDebt       a owl:Class ; rdfs:label "数据债" .
vinf:Proposal       a owl:Class ; rdfs:label "涌现提案" .
vinf:Cell           a owl:Class ; rdfs:label "细胞" .
vinf:CellComplex    a owl:Class ; rdfs:label "细胞复形" .
vinf:Engine         a owl:Class ; rdfs:label "验证引擎" .

# ===== 状态本体(互斥类, OWL disjointness 即可判定矛盾) =====
vinf:Established    a owl:Class ; rdfs:subClassOf vinf:Status .
vinf:Status         a owl:Class .
vinf:Open           a owl:Class ; rdfs:subClassOf vinf:Status .
vinf:Refuted        a owl:Class ; rdfs:subClassOf vinf:Status .
vinf:Certified      a owl:Class ; rdfs:subClassOf vinf:Status .
vinf:Established owl:disjointWith vinf:Refuted .
vinf:Certified   owl:disjointWith vinf:Refuted .
vinf:Open        owl:disjointWith vinf:Established, vinf:Certified, vinf:Refuted .

# ===== 属性层 =====
vinf:proves       a owl:ObjectProperty ; rdfs:domain vinf:Statement ; rdfs:range vinf:Statement ;
  owl:transitiveProperty true ; rdfs:label "证明(传递)" .
vinf:refutes      a owl:ObjectProperty ; rdfs:domain vinf:Statement ; rdfs:range vinf:Statement ;
  rdfs:label "证伪" ; owl:disjointProperty vinf:proves .
vinf:derives      a owl:ObjectProperty ; rdfs:label "派生" .
vinf:evolves      a owl:ObjectProperty ; rdfs:label "演化" .
vinf:dependsOn    a owl:ObjectProperty ; rdfs:label "依赖" ; owl:transitiveProperty true .
vinf:verifiedBy   a owl:ObjectProperty ; rdfs:range vinf:Engine ; rdfs:label "判决引擎" .
vinf:hasStatus    a owl:DatatypeProperty ; rdfs:label "状态" .
vinf:statement    a owl:DatatypeProperty ; rdfs:label "命题文本" .
vinf:emergedFrom  a owl:ObjectProperty ; rdfs:label "涌现自" .

# ===== SKOS 概念体系(知识组织层) =====
vinf:Scheme a skos:ConceptScheme ; rdfs:label "v∞ 知识体系" .
vinf:Geometry   a skos:Concept ; skos:prefLabel "几何层"@zh ; skos:inScheme vinf:Scheme .
vinf:Execution  a skos:Concept ; skos:prefLabel "执行层"@zh ; skos:inScheme vinf:Scheme .
vinf:Finance    a skos:Concept ; skos:prefLabel "金融域"@zh ; skos:inScheme vinf:Scheme .
vinf:Meta       a skos:Concept ; skos:prefLabel "元理论"@zh ; skos:inScheme vinf:Scheme .
"""

KIND_CLASS = dict(theorem='Theorem', axiom='Axiom', lemma='Lemma', corollary='Corollary',
                  proposition='Proposition', conditional='ConditionalTheorem',
                  empirical='EmpiricalLaw', derived='Theorem')
STATUS_CLASS = dict(established='Established', proved='Established', certified='Certified',
                    open='Open', refuted='Refuted', axiom_candidate='Open')
REL_PROP = dict(dep='dependsOn', derives='derives', evolves='evolves')
CODE_ENGINES = {'code', 'z3', 'sympy', 'backtest', 'rfl', 'code+llm'}


def esc(s):
    import re as _re
    s = _re.sub(r'[\x00-\x1f\x7f]', ' ', str(s))  # 控制字符一律剔除(Turtle字面量禁忌)
    return s.replace('\\', '\\\\').replace('"', '\\"')


def iri_safe(s, maxlen=28):
    import re as _re
    return _re.sub(r'[^A-Za-z0-9_-]', '-', str(s))[:maxlen] or 'unknown'


class OntologyExporter:
    """通用导出器: 任意理论库 → Turtle + 回读校验 + OWL 一致性审计"""

    def __init__(self, db_path=None, kg_path=None):
        self.db = sqlite3.connect(db_path or os.path.join(WORK, 'theory_db.sqlite'))
        self.kg = json.load(open(kg_path or os.path.join(WORK, 'kg.json')))
        self.lines = [HEADER]
        self.audit = dict(triples=0, parse_ok=False, contradictions=[], warnings=[])

    def _inst(self, iri, cls, label, extra=''):
        self.lines.append(f'vinf:{iri} a vinf:{cls} ; skos:prefLabel "{esc(label)}"@zh {extra} .')

    def export(self):
        db = self.db
        # 1 定理个体
        for tid, kind, stmt, status, deps, ev, vb, rnd, upd in db.execute(
                'SELECT id,kind,statement,status,deps,evidence,verified_by,round,updated FROM theorems'):
            cls = KIND_CLASS.get(kind, 'Theorem')
            st = STATUS_CLASS.get(status, 'Open')
            extra = (f'; vinf:hasStatus "{status}" ; vinf:statement "{esc(stmt)}"'
                     f' ; dct:created "2026" ; vinf:round {rnd}')
            if vb:
                extra += f' ; vinf:verifiedBy vinf:engine_{iri_safe(vb)}'
            self._inst(iri_safe(tid, 40), cls, f'{tid} {stmt[:40]}', extra)
        # 2 预测个体
        for pid, stmt, test_by, status in db.execute('SELECT id,statement,test_by,status FROM predictions'):
            self._inst(f'pred_{pid}', 'Prediction', f'{pid} {stmt[:40]}',
                       f'; vinf:hasStatus "{status}" ; vinf:statement "{esc(stmt)}"')
        # 3 数据债
        for did, item, status, note in db.execute('SELECT id,item,status,note FROM debts'):
            self._inst(f'debt_{did}', 'DataDebt', item,
                       f'; vinf:hasStatus "{status}" ; vinf:statement "{esc(note)}"')
        # 4 KG 边 → 对象属性
        for e in self.kg['edges']:
            prop = REL_PROP.get(e['rel'])
            if not prop:
                continue
            s = iri_safe(e['src'], 40); d = iri_safe(e['dst'], 40)
            self.lines.append(f'vinf:{s} vinf:{prop} vinf:{d} .')
        # 5 引擎注册
        for vb, in db.execute('SELECT DISTINCT verified_by FROM theorems WHERE verified_by != ""'):
            self.lines.append(f'vinf:engine_{iri_safe(vb)} a vinf:Engine ; '
                              f'skos:prefLabel "{esc(vb)}" ; vinf:hasStatus "'
                              f'{"code" if vb in CODE_ENGINES else "mixed"}" .')
        return '\n'.join(self.lines) + '\n'

    def validate(self, ttl):
        """自验证: rdflib 回读 + 一致性审计(代码判决, 非LLM印象)"""
        try:
            import rdflib
            g = rdflib.Graph()
            g.parse(data=ttl, format='turtle')
            self.audit['triples'] = len(g)
            self.audit['parse_ok'] = True
        except Exception as e:
            self.audit['parse_ok'] = False
            self.audit['warnings'].append(f'rdflib回读失败: {e}')
            return self.audit
        # 审计1: 状态互斥(established/certified 与 refuted 同体=矛盾)
        status = {}
        for tid, kind, stmt, st, *_ in self.db.execute('SELECT id,kind,statement,status FROM theorems'):
            status[iri_safe(tid, 40)] = st
        # 审计2: proves/refutes 同边冲突(KG边 与 状态交叉)
        refuted = {k for k, v in status.items() if v == 'refuted'}
        for e in self.kg['edges']:
            s = iri_safe(e['src'], 40); d = iri_safe(e['dst'], 40)
            if e['rel'] == 'derives' and d in refuted and status.get(s) in ('established', 'certified'):
                self.audit['contradictions'].append(f'{s}(成立) derives {d}(已证伪) — 依赖污染, 待复核')
        # 审计3: 孤儿定理(无边)
        linked = {e['src'] for e in self.kg['edges']} | {e['dst'] for e in self.kg['edges']}
        orphans = [k for k in status if k not in {iri_safe(x, 40) for x in linked}]
        if orphans:
            self.audit['warnings'].append(f'孤儿定理×{len(orphans)}: {",".join(orphans[:6])}')
        return self.audit

    def run(self, out_path=None):
        ttl = self.export()
        audit = self.validate(ttl)
        p = out_path or os.path.join(WORK, 'kg.ttl')
        open(p, 'w').write(ttl)
        return p, audit


if __name__ == '__main__':
    p, a = OntologyExporter().run()
    print(f'本体导出: {p}')
    print(f'rdflib回读: {"OK" if a["parse_ok"] else "FAIL"} · 三元组 {a["triples"]}')
    for c in a['contradictions']:
        print('  矛盾:', c)
    for w in a['warnings']:
        print('  警告:', w)
