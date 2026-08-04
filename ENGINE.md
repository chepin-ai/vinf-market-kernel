# v∞ Engine — 自证伪理论机器 · 通用工程化引擎

**版本 2.6.0 · 第 55 章定版 · 通用可复用（换 workdir 即换域）**

一台会自我证伪的知识引擎：命题以哈希链记账、由代码判决真值、经语义网标准暴露、
靠多智能体涌现生长、由医官自修复——金融市场是其当前运行域，而非其本质。

---

## 1. 五分钟上手（第三方）

```bash
git clone https://github.com/chepin-ai/vinf-market-kernel.git
cd vinf-market-kernel
pip install pandas numpy sympy rdflib z3-solver   # z3 可选
python3 engine.py            # info: 版本+链状态+协议
python3 engine.py verify     # 哈希链完整性(无需信任任何服务器)
python3 engine.py doctor     # 六面自检/自修复
python3 engine.py reason     # 自推演/自验证/自涌现报告
python3 engine.py ttl        # 导出 RDF/Turtle 语义网表示(kg.ttl)
python3 test_engine.py       # 十项契约自测试
```

## 2. Python API

```python
from engine import Engine
e = Engine('/path/to/kernel')   # 需含 theory_db.sqlite / journal39.jsonl / kg.json
e.verify()        # 链完整性 → {'ok','hops','tail'}
e.status()        # 状态包(链/库/金融四检/债/sorry)
e.doctor()        # 自检+静默自修复 → doctor_report
e.reason()        # 推理机: deductions/topology/sympy_xval/emergent
e.export_ttl()    # → (kg.ttl路径, audit)  SKOS/OWL/vinf本体
e.finance()       # 金融四检 F1–F4(代码判决)
e.refresh_cn()    # iFinD增量刷新CN系(多源容灾+多日分块)
e.run('DOCTOR')   # 命令注册表执行
e.commands()      # 可用命令列表
```

## 3. 架构（引擎=五面十二机）

| 面 | 模块 | 职责 |
|---|---|---|
| 记账 | journal39.jsonl + vinf_console | 哈希链(prev_hash→hash)，断链即停 |
| 内核 | vinf_os(Kernel39) · theory_db.sqlite | tick: 闭包推演/sorry消解/池演化 |
| 判决 | vinf_finance · sympy · z3 · backtest | 命题状态唯一合法变更者(A2/T9) |
| 推演 | vinf_reasoner | 前向链闭包/拓扑审计(χ=β0-β1+β2)/涌现注入 |
| 语义 | vinf_ontology | RDF/Turtle+SKOS/OWL/vinf本体，rdflib回读 |
| 医疗 | vinf_doctor | 六面自检/静默自修复/遗留登记 |
| 命令 | vinf_commands | RUN <CMD> 注册表，响应闭环唯一语义源 |
| 数据 | vinf_refresh_cn · ci_finance · vinf_market | 多源容灾(Yahoo→FRED→Stooq→iFinD→本地) |
| 门面 | engine.py | 第三方统一入口 |
| 自测 | test_engine.py | 十项契约，push/每日自动跑 |
| 协作 | agents_registry.json · vinf_agents | 多智能体泳道分工(预算制) |
| 展示 | Dashboard(SCADA) | 只读审计面，人在回路 |

## 4. 不可协商协议

1. **Git-first**：restore→verify→tick→push，禁止种子重建。
2. **代码才判决（A2/T9）**：LLM 只提议，命题状态仅由代码变更。
3. **人在回路**：浏览器/外部只读；写操作经命令注册表由人触发。
4. **密钥不出境**：vinf_keys.json/大数据永不入 Git（.gitignore 强制）。
5. **涌现须蒸馏（R7）**：一切涌现物 raw-need-distill → 蒸馏 → 代码判决 → 升格。
6. **诚实缺口**：数据缺失去登记台账+健康面板亮红，禁止伪造。

## 5. 自\*能力矩阵

| 能力 | 实现 | 验证 |
|---|---|---|
| 自推演 | 前向链闭包+状态传播(vinf_reasoner) | reasoner_report.deductions |
| 自验证 | 拓扑审计/OWL互斥/rdflib回读/sympy交叉 | audit.parse_ok · topology.ok |
| 自修复 | 医官六面巡检(状态滞后/资产陈旧/bundle过期) | doctor_report.repairs |
| 自涌现 | 推理产物→提案池(R7门禁) | pool.json R*条目 |
| 自证伪 | F1–F4金融检验+锐利/深度证伪泳道 | finance verdicts |
| 自测试 | 十项契约(test_engine.py) | selftest_report.json |

## 6. 命令注册表

`REFRESH-CN`(iFinD增量) · `REFRESH-CN-FULL`(1090天分块回补) · `FIN-STATUS`(重跑四检)
· `DOCTOR`(巡检) · `BUNDLE`(重建状态包) · `ONTOLOGY`(本体+推理机)

Dashboard 告警的响应指令单携带 RUN 令牌；粘贴回 v∞ 会话即确定性执行，
command_log.jsonl 留痕，疗效=告警消除+入链。

## 7. 换域指南（通用性）

引擎不绑定领域：替换 `theory_db.sqlite`(theorems/predictions/debts/frontier 四表)、
`kg.json`(nodes/edges)、`state_bundle.json` 三件套即换域。本体层/推理机/医官/命令
注册表零修改复用。金融四检为可插拔示例——仿照 vinf_finance.FinanceEngine 写
`<domain>_checks.py` 即可接入新域的代码判决。
