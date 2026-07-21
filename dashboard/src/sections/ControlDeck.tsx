import { useMemo, useState } from 'react';
import type { Bundle } from '../lib/kernel';

// 人在回路控制台: 调参 → 生成指令单(不直连写权限, 人携带指令回kernel会话——这是刻意的安全设计)
interface Param {
  key: string; label: string; value: number; min: number; max: number; step: number;
  desc: string;
}

const DEFAULTS: Param[] = [
  { key: 'budget_llm', label: 'LLM预算/跳', value: 12, min: 0, max: 40, step: 1, desc: '单次tick的LLM调用上限(熔断)' },
  { key: 'temp_start', label: '搜索初温', value: 0.4, min: 0.1, max: 1.0, step: 0.05, desc: 'sorry搜索温度起点(探索)' },
  { key: 'temp_decay', label: '温度衰减', value: 0.1, min: 0.02, max: 0.3, step: 0.01, desc: '每轮降温(探索→利用)' },
  { key: 'pool_cull', label: '池容量', value: 20, min: 5, max: 60, step: 5, desc: '提案池cull保留数' },
  { key: 'escalate_max', label: '升格阈值', value: 3, min: 2, max: 6, step: 1, desc: '连败几次升格为公理候选' },
  { key: 'fin_enabled', label: '金融四检', value: 1, min: 0, max: 1, step: 1, desc: '1=每跳自动复检 0=暂停' },
];

export default function ControlDeck({ bundle }: { bundle: Bundle }) {
  const [params, setParams] = useState<Param[]>(DEFAULTS);
  const [ticket, setTicket] = useState<string>('');
  const [copied, setCopied] = useState(false);

  const dirty = params.some((p, i) => p.value !== DEFAULTS[i].value);

  const ticketJson = useMemo(() => {
    const patch = Object.fromEntries(
      params.filter((p, i) => p.value !== DEFAULTS[i].value).map((p) => [p.key, p.value]),
    );
    return {
      type: 'v∞/policy-patch',
      issued: new Date().toISOString(),
      patch,
      apply: '粘贴本指令到v∞会话(任意心跳/对话)即生效; 由代码写入policy并登记journal',
      governance: 'A2′/T9: 参数变更须经代码执行并留哈希链记录',
    };
  }, [params]);

  const currentPolicy = bundle.policy;

  return (
    <div className="space-y-3">
      <div className="rounded border border-amber-500/30 bg-amber-500/5 p-2 font-mono text-[10px] leading-relaxed text-amber-200/80">
        ⛑ 人在回路 by design: 浏览器不持有写凭据。调参生成「指令单」，由你粘贴回任意 v∞ 会话/心跳，
        代码落盘并留链——人是内核的root权限。
      </div>
      {params.map((p, i) => (
        <div key={p.key}>
          <div className="flex items-center justify-between font-mono text-[11px]">
            <span className="text-slate-300">{p.label}</span>
            <span className={p.value !== DEFAULTS[i].value ? 'text-amber-300' : 'text-cyan-300'}>{p.value}</span>
          </div>
          <input
            type="range" min={p.min} max={p.max} step={p.step} value={p.value}
            onChange={(e) => {
              const v = Number(e.target.value);
              setParams(params.map((q, j) => (j === i ? { ...q, value: v } : q)));
            }}
            className="w-full accent-cyan-400"
          />
          <p className="font-mono text-[9px] text-slate-600">{p.desc}</p>
        </div>
      ))}
      <button
        disabled={!dirty}
        onClick={() => setTicket(JSON.stringify(ticketJson, null, 2))}
        className="w-full rounded border border-cyan-500/50 bg-cyan-500/10 py-1.5 font-mono text-xs text-cyan-300 transition enabled:hover:bg-cyan-500/25 disabled:opacity-30"
      >
        ⚙ 生成调参指令单
      </button>
      {ticket && (
        <div className="relative">
          <pre className="max-h-44 overflow-auto rounded border border-slate-600 bg-slate-950 p-2 font-mono text-[10px] text-emerald-300">{ticket}</pre>
          <button
            onClick={() => { navigator.clipboard.writeText(ticket); setCopied(true); setTimeout(() => setCopied(false), 1500); }}
            className="absolute right-2 top-2 rounded border border-slate-500 bg-slate-800 px-2 py-0.5 font-mono text-[10px] text-slate-300 hover:bg-slate-700"
          >
            {copied ? '✓已复制' : '复制'}
          </button>
        </div>
      )}
      <div className="border-t border-slate-800 pt-2">
        <p className="mb-1 font-mono text-[10px] tracking-widest text-slate-500">现行章法(只读镜像)</p>
        {Object.entries(currentPolicy.roles).map(([role, r]) => (
          <div key={role} className="flex items-baseline gap-2 font-mono text-[10px]">
            <span className="w-28 shrink-0 text-cyan-300/80">{role}</span>
            <span className="text-slate-500">{r.lane}/{r.model.split('-').pop()}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
