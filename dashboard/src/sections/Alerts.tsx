import { useState } from 'react';
import type { Bundle } from '../lib/kernel';

// 告警与即时响应: 异常从状态包实时计算, 每条配响应指令单
export interface Alert { sev: 'crit' | 'warn' | 'info'; msg: string; response: string }

export function computeAlerts(b: Bundle, source: string): Alert[] {
  const out: Alert[] = [];
  if (!b.status.chain.ok)
    out.push({ sev: 'crit', msg: `哈希链断裂: ${b.status.chain.detail ?? ''}`, response: '停止一切写入! 运行 python3 vinf_console.py verify 定位断点, 从GitHub恢复最近一致快照' });
  const last = b.status.last_tick ? new Date(b.status.last_tick.replace(' ', 'T')) : null;
  if (last && Date.now() - last.getTime() > 4 * 864e5)
    out.push({ sev: 'warn', msg: `心跳失联>4天(末跳 ${b.status.last_tick})`, response: '检查cron任务19f80a04是否存活; 手动执行 vinf_console.py tick 补跳' });
  if (source !== 'github-live')
    out.push({ sev: 'warn', msg: '当前为快照数据(非GitHub实时)', response: '检查网络/raw.githubusercontent可达性; 或等下一跳刷新' });
  for (const f of b.status.finance) {
    if (f.includes('fail'))
      out.push({ sev: 'crit', msg: `金融检验失败: ${f.slice(0, 60)}`, response: '复核对应数据文件与检验代码; 若理论被证伪, 登记并启动池演化寻找修正变体' });
    if (f.includes('skip'))
      out.push({ sev: 'info', msg: `金融检验跳过: ${f.slice(0, 60)}`, response: '补齐对应数据资产(见数据债台账)' });
  }
  for (const d of b.debts.filter((x) => x.status !== 'closed'))
    out.push({ sev: 'info', msg: `数据债open: ${d.item}`, response: d.note ? `按note执行: ${d.note.slice(0, 50)}` : '等数据源更新' });
  if (b.conflicts.length)
    out.push({ sev: 'crit', msg: `知识库冲突×${b.conflicts.length}`, response: '冲突须由代码判决: 为冲突双方各写可执行检验, 败方降级, 过程留链' });
  for (const p of b.pool.filter((x) => x.status === 'raw-need-distill'))
    out.push({ sev: 'info', msg: `池条目待蒸馏: ${p.id}`, response: '按章法R7: 经蒸馏提取命题本体后方可准入' });
  const ax = b.theorems.filter((t) => t.status === 'axiom_candidate');
  if (ax.length)
    out.push({ sev: 'info', msg: `公理候选待证: ${ax.map((t) => t.id).join(',')}`, response: '排入sorry流水线: rfl→LLM→搜索; 或接受为条件定理并标注假设' });
  return out;
}

const SEV = {
  crit: { c: '#fb7185', bg: 'bg-rose-500/10 border-rose-500/40', label: 'CRIT' },
  warn: { c: '#fbbf24', bg: 'bg-amber-500/10 border-amber-500/40', label: 'WARN' },
  info: { c: '#60a5fa', bg: 'bg-blue-500/10 border-blue-500/40', label: 'INFO' },
};

export default function Alerts({ alerts }: { alerts: Alert[] }) {
  const [copied, setCopied] = useState<number | null>(null);
  if (!alerts.length)
    return <p className="font-mono text-xs text-emerald-400">✓ 无告警 — 全部机制运行正常</p>;
  return (
    <div className="space-y-1.5">
      {alerts.map((a, i) => (
        <div key={i} className={`rounded border p-2 ${SEV[a.sev].bg}`}>
          <div className="flex items-center gap-2">
            <span className="font-mono text-[10px] font-bold" style={{ color: SEV[a.sev].c }}>{SEV[a.sev].label}</span>
            <span className="font-mono text-[11px] text-slate-300">{a.msg}</span>
            <button
              onClick={() => { navigator.clipboard.writeText(`[v∞响应指令] ${a.response}`); setCopied(i); setTimeout(() => setCopied(null), 1200); }}
              className="ml-auto shrink-0 rounded border border-slate-500/50 px-1.5 py-0.5 font-mono text-[9px] text-slate-400 hover:bg-slate-700"
            >
              {copied === i ? '✓' : '⚡响应'}
            </button>
          </div>
          <p className="mt-0.5 font-mono text-[9px] text-slate-500">→ {a.response}</p>
        </div>
      ))}
    </div>
  );
}
