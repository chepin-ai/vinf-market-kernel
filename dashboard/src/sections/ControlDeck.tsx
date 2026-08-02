import { useMemo, useState } from 'react';
import type { Bundle } from '../lib/kernel';

// 人在回路控制台: 调参→影响预览(导致的改变/结果)→恢复Default→指令单
interface Param {
  key: string; label: string; value: number; min: number; max: number; step: number;
  desc: string; unit?: string;
}
const DEFAULTS: Param[] = [
  { key: 'budget_llm', label: 'LLM预算/跳', value: 12, min: 0, max: 40, step: 1, desc: '单次tick的LLM调用上限(熔断)' },
  { key: 'temp_start', label: '搜索初温', value: 0.4, min: 0.1, max: 1.0, step: 0.05, desc: 'sorry搜索温度起点(探索)' },
  { key: 'temp_decay', label: '温度衰减', value: 0.1, min: 0.02, max: 0.3, step: 0.01, desc: '每轮降温(探索→利用)' },
  { key: 'pool_cull', label: '池容量', value: 20, min: 5, max: 60, step: 5, desc: '提案池cull保留数' },
  { key: 'escalate_max', label: '升格阈值', value: 3, min: 2, max: 6, step: 1, desc: '连败几次升格为公理候选' },
  { key: 'fin_enabled', label: '金融四检', value: 1, min: 0, max: 1, step: 1, desc: '1=每跳自动复检 0=暂停' },
];

// 影响模型: 每条变更的可预期后果(规则化, 基于39-42章实测)
function impacts(p: Param, def: number): string[] {
  const d = p.value - def;
  if (!d) return [];
  switch (p.key) {
    case 'budget_llm':
      return d > 0
        ? [`每跳sorry消解尝试↑: 预计多消解 ~${Math.max(1, Math.round(d / 4))} 项/跳`, '成本线性↑', 'T31/T29等形式化攻坚可并行', '熔断保护不变']
        : [`LLM近静默: 仅剩代码层(closure/forge/finance)继续`, '成本↓至≈0', 'sorry队列冻结——自演化降级为自维护'];
    case 'temp_start':
      return d > 0
        ? ['探索性↑: 新证明路线发现率↑', '脚本一次可用率↓(实测6/6失败率将恶化)', '建议配合budget↑']
        : ['利用性↑: 更保守的证明路线', '突变能力↓, 易陷局部(重复同一失败路线)'];
    case 'temp_decay':
      return d > 0
        ? ['降温快: 更快锁定可行路线', '多样性损失: 搜索树变浅', '适合rfl可解型任务']
        : ['降温慢: 长时间保持探索', '每题消耗轮次↑', '适合T29级难题'];
    case 'pool_cull':
      return d > 0
        ? ['多样性记忆↑: 更多失败祖先被保留(罚金库↑)', '适应度稀释风险↑', '交叉材料更丰富']
        : ['精英化: 只有最强变体存活', '多样性塌缩风险——近亲繁殖', '演化可能收敛到单一思路'];
    case 'escalate_max':
      return d > 0
        ? [`证明耐心↑: 每题多${d}次尝试`, `资源消耗↑~${Math.round((d / 3) * 100)}%`, '公理候选更难产生——边界收紧']
        : ['更快升格: 不可解题早止损', '风险: 本可证明的题被过早放弃(假边界)'];
    case 'fin_enabled':
      return p.value === 0
        ? ['金融四检暂停: 每跳省2次数据扫描', 'VRP制度漂移不可见——F1-F3失效将无告警', '不建议长期关闭']
        : ['金融四检恢复: 每跳自动复检E5/T13/L7'];
    default:
      return [];
  }
}

export default function ControlDeck({ bundle }: { bundle: Bundle }) {
  const [params, setParams] = useState<Param[]>(DEFAULTS);
  const [ticket, setTicket] = useState('');
  const [copied, setCopied] = useState(false);
  const dirty = params.some((p, i) => p.value !== DEFAULTS[i].value);

  const ticketJson = useMemo(() => ({
    type: 'v∞/policy-patch',
    issued: new Date().toISOString(),
    patch: Object.fromEntries(params.filter((p, i) => p.value !== DEFAULTS[i].value).map((p) => [p.key, p.value])),
    apply: '粘贴本指令到v∞会话(任意心跳/对话)即生效; 由代码写入policy并登记journal',
    governance: 'A2′/T9: 参数变更须经代码执行并留哈希链记录',
  }), [params]);

  const allImpacts = params.flatMap((p, i) => impacts(p, DEFAULTS[i].value).map((s) => ({ key: p.key, label: p.label, s })));

  return (
    <div className="space-y-3">
      <div className="rounded border border-amber-500/30 bg-amber-500/5 p-2 font-mono text-[10px] leading-relaxed text-amber-200/80">
        ⛑ 人在回路 by design: 浏览器不持有写凭据。调参先预览影响, 再生成「指令单」由你粘贴回
        v∞ 会话生效、代码落盘留链——人是内核的root权限。
      </div>
      {params.map((p, i) => (
        <div key={p.key}>
          <div className="flex items-center justify-between font-mono text-[11px]">
            <span className="text-slate-300">{p.label}</span>
            <span className={p.value !== DEFAULTS[i].value ? 'text-amber-300' : 'text-cyan-300'}>
              {p.value}{p.value !== DEFAULTS[i].value && <span className="text-slate-600"> (默认{DEFAULTS[i].value})</span>}
            </span>
          </div>
          <input type="range" min={p.min} max={p.max} step={p.step} value={p.value}
            onChange={(e) => setParams(params.map((q, j) => (j === i ? { ...q, value: Number(e.target.value) } : q)))}
            className="w-full accent-cyan-400" />
          {p.value !== DEFAULTS[i].value && (
            <div className="mt-0.5 space-y-0.5 rounded border border-amber-500/20 bg-amber-500/5 p-1.5">
              {impacts(p, DEFAULTS[i].value).map((s, k) => (
                <p key={k} className="font-mono text-[9px] leading-snug text-amber-200/80">⇒ {s}</p>
              ))}
            </div>
          )}
          <p className="font-mono text-[9px] text-slate-600">{p.desc}</p>
        </div>
      ))}
      <div className="flex gap-1.5">
        <button disabled={!dirty} onClick={() => setTicket(JSON.stringify(ticketJson, null, 2))}
          className="flex-1 rounded border border-cyan-500/50 bg-cyan-500/10 py-1.5 font-mono text-xs text-cyan-300 enabled:hover:bg-cyan-500/25 disabled:opacity-30">
          ⚙ 生成指令单
        </button>
        <button disabled={!dirty} onClick={() => { setParams(DEFAULTS); setTicket(''); }}
          className="rounded border border-slate-500/60 bg-slate-800/50 px-3 py-1.5 font-mono text-xs text-slate-300 enabled:hover:bg-slate-700 disabled:opacity-30">
          ⟲ 恢复Default
        </button>
      </div>
      {allImpacts.length > 0 && (
        <div className="rounded border border-cyan-500/25 bg-cyan-500/5 p-2">
          <p className="mb-1 font-mono text-[10px] tracking-widest text-cyan-300">变更总账({allImpacts.length}条后果)</p>
          {allImpacts.map((x, k) => (
            <p key={k} className="font-mono text-[9px] text-slate-400">[{x.label}] {x.s}</p>
          ))}
        </div>
      )}
      {ticket && (
        <div className="relative">
          <pre className="max-h-40 overflow-auto rounded border border-slate-600 bg-slate-950 p-2 font-mono text-[10px] text-emerald-300">{ticket}</pre>
          <button onClick={() => { navigator.clipboard.writeText(ticket); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
            className="absolute right-2 top-2 rounded border border-slate-500 bg-slate-800 px-2 py-0.5 font-mono text-[10px] text-slate-300 hover:bg-slate-700">
            {copied ? '✓已复制' : '复制'}
          </button>
        </div>
      )}
      <div className="border-t border-slate-800 pt-2">
        <p className="mb-1 font-mono text-[10px] tracking-widest text-slate-500">现行章法(只读镜像)</p>
        {Object.entries(bundle.policy.roles).map(([role, r]) => (
          <div key={role} className="flex items-baseline gap-2 font-mono text-[10px]">
            <span className="w-28 shrink-0 text-cyan-300/80">{role}</span>
            <span className="text-slate-500">{r.lane}/{r.model.split('-').pop()}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
