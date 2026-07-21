import type { Bundle } from '../lib/kernel';
import { STATUS_STYLE } from '../lib/kernel';

// 多符号引擎 & 形式化推理引擎运行板: 真实胜场来自定理注册表
const ENGINES = [
  { id: 'z3', name: 'Z3 · SMT', color: '#34d399', domain: '量化逻辑/算术/代数公理', wins: ['SORRY-T1', 'AX-MAX'] },
  { id: 'sympy', name: 'sympy · 代数', color: '#2dd4bf', domain: '恒等式/不等式/凸性/积分闭式', wins: ['GIBBS-2', 'RENYI-MONO(闭式)'] },
  { id: 'numeric', name: '数值证书', color: '#60a5fa', domain: '网格/区间证书(半形式)', wins: ['RENYI-MONO(单调性)'] },
  { id: 'gf2', name: 'GF(2)同调', color: '#f472b6', domain: '知识细胞复形 Betti数', wins: ['β₁=1 独立环检出'] },
  { id: 'lean', name: 'Lean(外挂)', color: '#a78bfa', domain: '全形式证明', wins: ['MarketKernel.lean ×11(人工)'] },
];

const PIPELINE = [
  { stage: '① rfl速解', desc: '自动证明器直证', res: 'T1✓ AX-MAX✓ GIBBS-2✓', color: '#34d399' },
  { stage: '② LLM直证', desc: 'LLM写脚本,代码执行,30s熔断,自愈手术', res: 'RENYI→经证书通道认证', color: '#2dd4bf' },
  { stage: '③ 搜索', desc: '温度0.4→0.1+失败记忆', res: '6/6直出失败→R8规则诞生', color: '#fbbf24' },
  { stage: '④ 升格', desc: '连败≥3→公理候选', res: 'T29→axiom_candidate', color: '#a78bfa' },
];

export default function ProverBoard({ bundle }: { bundle: Bundle }) {
  const resolved = bundle.theorems.filter((t) => t.kind === 'sorry-resolution' || t.id === 'T29');
  return (
    <div className="space-y-3">
      <div className="grid grid-cols-1 gap-2 md:grid-cols-5">
        {ENGINES.map((e) => (
          <div key={e.id} className="rounded border border-slate-700/60 bg-slate-800/40 p-2" style={{ borderTopColor: e.color, borderTopWidth: 2 }}>
            <p className="font-mono text-xs" style={{ color: e.color }}>{e.name}</p>
            <p className="mt-1 font-mono text-[9px] text-slate-500">{e.domain}</p>
            <div className="mt-1 space-y-0.5">
              {e.wins.map((w) => (
                <p key={w} className="font-mono text-[9px] text-slate-300">✓ {w}</p>
              ))}
            </div>
          </div>
        ))}
      </div>
      <div className="grid grid-cols-1 gap-2 md:grid-cols-4">
        {PIPELINE.map((p) => (
          <div key={p.stage} className="rounded border border-slate-700/60 bg-slate-900/60 p-2">
            <p className="font-mono text-[11px]" style={{ color: p.color }}>{p.stage}</p>
            <p className="font-mono text-[9px] text-slate-500">{p.desc}</p>
            <p className="mt-1 font-mono text-[9px] text-slate-300">{p.res}</p>
          </div>
        ))}
      </div>
      <div>
        <p className="mb-1 font-mono text-[10px] tracking-widest text-slate-500">sorry 消解台账(注册表实录)</p>
        <div className="space-y-1">
          {resolved.map((t) => (
            <div key={t.id} className="flex items-center gap-2 font-mono text-[11px]">
              <span className="w-28 truncate text-slate-300">{t.id}</span>
              <span className={`rounded border px-1.5 py-0.5 text-[10px] ${STATUS_STYLE[t.status] ?? ''}`}>{t.status}</span>
              <span className="text-[10px] text-slate-500">{t.verified_by}</span>
              <span className="ml-auto hidden truncate text-[10px] text-slate-600 md:inline">{t.statement.slice(0, 40)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
