import { useState } from 'react';
import type { Bundle } from '../lib/kernel';

// 蜂群运行视图: 真实T30案回放(日志实录) + 通道/泳道/协议
const T30_SCRIPT = [
  { actor: 'deepseek-v4-pro', role: '立论', color: '#60a5fa', text: '候选T30: 协议税 τ=κ(1−c), c=D₁/D∞; 预测 τ(CS)>τ(1X2)>τ(O/U)' },
  { actor: 'distiller', role: '蒸馏', color: '#94a3b8', text: '推理链→80字净陈述(推理型模型自适应补丁)' },
  { actor: 'kimi-k2.6', role: '证伪·否决', color: '#fb7185', text: '同义反复: τ与c的关系由定义产生,"预测"只是数学变形; κ跨市场恒定是隐藏假设' },
  { actor: 'deepseek-v4-flash', role: '证伪·通过', color: '#fbbf24', text: '通过(但标注同一隐藏假设)——flash漏报, 印证R2不对称权重必要性' },
  { actor: 'T26聚合器', role: 'sup否决', color: '#a78bfa', text: 'kills=[kimi] → veto, 驳回。异构先验分歧即区分器价值' },
  { actor: 'Verifier(代码)', role: '核验', color: '#34d399', text: '经验残差: CS 26% ≫ 1X2 3.3-10% ≈ totals ~5%, 三数据集复现 → 登记经验规律E4' },
];

export default function SwarmView({ bundle }: { bundle: Bundle }) {
  const [step, setStep] = useState(0);
  const playing = step < T30_SCRIPT.length;

  return (
    <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
      {/* 泳道图 */}
      <div className="space-y-2">
        <p className="font-mono text-[10px] tracking-widest text-slate-500">泳道拓扑(章法R1-R8)</p>
        {Object.entries(bundle.policy.lanes).map(([lane, desc]) => (
          <div key={lane} className="rounded border border-slate-700/60 bg-slate-800/40 p-2">
            <div className="flex items-center gap-2">
              <span className={`h-2 w-2 rounded-full ${lane === 'kimi' ? 'bg-rose-400' : lane === 'deepseek' ? 'bg-blue-400' : 'bg-amber-400'}`} />
              <span className="font-mono text-xs text-slate-200">{lane}</span>
              <span className="font-mono text-[10px] text-slate-600">{(bundle.policy.roles as Record<string, { lane: string }>).hasOwnProperty(lane) ? '' : ''}</span>
            </div>
            <p className="mt-0.5 font-mono text-[10px] text-slate-500">{desc}</p>
          </div>
        ))}
        <div className="rounded border border-violet-500/30 bg-violet-500/5 p-2">
          <p className="font-mono text-[10px] text-violet-300">协作协议</p>
          <p className="mt-0.5 font-mono text-[10px] leading-relaxed text-slate-400">
            T26: 共识=均值池(证据取mean) · 否决=最大池(异议取sup, 任一致命伤即驳回)<br />
            A2′/T9: LLM只提案, 代码才判决 · R1: 终审证伪≥2厂商 · R2: flash通过不计票
          </p>
        </div>
      </div>
      {/* T30案回放 */}
      <div>
        <div className="mb-2 flex items-center justify-between">
          <p className="font-mono text-[10px] tracking-widest text-slate-500">实录回放: T30案(首次自证伪活体)</p>
          <div className="flex gap-1">
            <button onClick={() => setStep(0)} className="rounded border border-slate-600 px-2 py-0.5 font-mono text-[10px] text-slate-400 hover:bg-slate-800">⟲</button>
            <button
              onClick={() => setStep(Math.min(step + 1, T30_SCRIPT.length))}
              disabled={!playing}
              className="rounded border border-cyan-500/50 bg-cyan-500/10 px-2 py-0.5 font-mono text-[10px] text-cyan-300 enabled:hover:bg-cyan-500/25 disabled:opacity-30"
            >
              {playing ? `▶ 第${step + 1}步` : '✓ 完'}
            </button>
          </div>
        </div>
        <div className="space-y-1.5">
          {T30_SCRIPT.slice(0, step).map((s, i) => (
            <div key={i} className="rounded border-l-2 bg-slate-800/40 p-2" style={{ borderColor: s.color }}>
              <div className="flex items-center gap-2 font-mono text-[10px]">
                <span style={{ color: s.color }}>{s.actor}</span>
                <span className="text-slate-600">{s.role}</span>
              </div>
              <p className="mt-0.5 text-[11px] leading-relaxed text-slate-400">{s.text}</p>
            </div>
          ))}
          {step === 0 && <p className="font-mono text-[10px] text-slate-600">按 ▶ 逐步回放六幕</p>}
        </div>
      </div>
    </div>
  );
}
