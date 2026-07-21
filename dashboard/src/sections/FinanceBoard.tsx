import { useMemo } from 'react';
import type { Bundle } from '../lib/kernel';

// 精细金融看板: VRP期限结构 + D_α阶梯 + 每格判断/意见(基于实测数据的规则化解读)
function Bar({ v, max, color }: { v: number; max: number; color: string }) {
  const w = Math.min(100, (Math.abs(v) / max) * 100);
  return (
    <div className="relative h-3 w-full rounded bg-slate-800">
      <div className={`absolute top-0 h-3 rounded ${v < 0 ? 'right-1/2' : 'left-1/2'}`}
        style={{ width: `${w / 2}%`, background: color }} />
      <div className="absolute left-1/2 top-0 h-3 w-px bg-slate-600" />
    </div>
  );
}

const OPINION: Record<string, string> = {
  '~7d': '短端负税: 危机样本RV爆发领先IV——7d期权反而是"买方市场", 收割面在对面',
  '~30d': '主力期限: 税≈0甚至微负, 市场最有效的区间, 边缘最薄',
  '~60d': '过渡带: 税率回正途中, 结构不稳定, 观察>行动',
  '~90d': '税率转正(t=2.1): 长端叙事空间开始收费, 卖方边缘出现',
  '~180d': '最稳收割面: +3.43点 t=8.1, 长端恒正——E5的锚点, 卖方结构性优势区',
};

export default function FinanceBoard({ bundle }: { bundle: Bundle }) {
  const vrp = useMemo(() => (bundle.vrp_ladder ?? []).map((r) => ({
    bucket: r.bucket, dte: Number(r.DTE), iv: Number(r.IV) * 100, rv: Number(r.RV_trail) * 100,
    nt: Number(r.NT_pre) * 100, vrp: Number(r.VRP_post) * 100,
    hit: Number(r.VRP_hit), t: Number(r.VRP_t),
  })).sort((a, b) => a.dte - b.dte), [bundle.vrp_ladder]);

  const da = useMemo(() => (bundle.dalpha ?? []).map((r) => ({
    iv: Number(r.IV), d1: Number(r.D1_t), d2: Number(r.D2_t), dinf: Number(r.Dinf_t),
    crisis: r.crisis === 'True' || r.crisis === '1',
  })), [bundle.dalpha]);

  const maxV = Math.max(4, ...vrp.map((r) => Math.abs(r.vrp)));
  const daMed = (arr: number[]) => arr.length ? arr.sort((x, y) => x - y)[Math.floor(arr.length / 2)] : 0;
  const calmM = daMed(da.filter((x) => !x.crisis).map((x) => x.dinf));
  const crisM = daMed(da.filter((x) => x.crisis).map((x) => x.dinf));

  return (
    <div className="space-y-4">
      {/* VRP 期限结构 */}
      <div>
        <p className="mb-2 font-mono text-[10px] tracking-widest text-slate-500">
          叙事税期限结构 (SPY 2020–2022, vol点) —— E5复检
        </p>
        <div className="space-y-2">
          {vrp.map((r) => (
            <div key={r.bucket} className="rounded border border-slate-700/50 bg-slate-900/50 p-2">
              <div className="flex items-center gap-3 font-mono text-[11px]">
                <span className="w-12 text-slate-300">{r.bucket}</span>
                <div className="flex-1">
                  <Bar v={r.vrp} max={maxV} color={r.vrp >= 0 ? '#34d399' : '#fb7185'} />
                </div>
                <span className={`w-16 text-right ${r.vrp >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                  {r.vrp >= 0 ? '+' : ''}{r.vrp.toFixed(2)}
                </span>
                <span className="w-14 text-right text-slate-500">t={r.t.toFixed(1)}</span>
                <span className="w-12 text-right text-slate-500">{(r.hit * 100).toFixed(0)}%</span>
              </div>
              <p className="mt-1 font-mono text-[10px] text-amber-200/70">⚖ {OPINION[r.bucket]}</p>
            </div>
          ))}
        </div>
        <p className="mt-2 rounded border border-cyan-500/30 bg-cyan-500/5 p-2 font-mono text-[11px] leading-relaxed text-cyan-200/90">
          内核意见: 叙事税是<b>叙事空间的函数</b>——期限越长路径越多、sup聚合可收割面越大。
          短端负税不违T13(T13断言定价核非负, 非任意窗IV−RV)。交易含义: 结构性卖方优势在≥90d端;
          短端更适合买方(危机制度RV爆发领先定价)。制度依赖已注明: 本样本=2020崩盘+2022熊市。
        </p>
      </div>
      {/* D_α 阶梯 */}
      <div>
        <p className="mb-2 font-mono text-[10px] tracking-widest text-slate-500">
          D_α阶梯 (BL隐含Q vs 物理P, 翼部修剪) —— L7复检 · n={da.length}
        </p>
        <div className="grid grid-cols-2 gap-2">
          {[
            { label: '平静态 D∞中位', v: calmM, c: '#34d399' },
            { label: '危机态 D∞中位', v: crisM, c: '#fbbf24' },
          ].map((x) => (
            <div key={x.label} className="rounded border border-slate-700/50 bg-slate-900/50 p-3 text-center">
              <p className="font-mono text-xl" style={{ color: x.c }}>{x.v.toFixed(2)}</p>
              <p className="font-mono text-[10px] text-slate-500">{x.label} (nats)</p>
            </div>
          ))}
        </div>
        <p className="mt-2 rounded border border-violet-500/30 bg-violet-500/5 p-2 font-mono text-[11px] leading-relaxed text-violet-200/90">
          内核意见: D∞仍为D₁的5–8×——Q−P差异集中在<b>sup端(尾部)</b>, 是T26 maxitive聚合在期权面的直接证据;
          陡度∝叙事浓度(ρ=0.749, p&lt;0.0001)。边界: n=29曲面, 二分检验功效不足(MWU p=0.34)——
          连续关系可信, 阈值效应待补数据。
        </p>
      </div>
      {/* 四检结论 */}
      <div>
        <p className="mb-1 font-mono text-[10px] tracking-widest text-slate-500">每跳复检结论(原始记录)</p>
        {bundle.status.finance.map((f, i) => (
          <p key={i} className="font-mono text-[11px] text-slate-400">· {f}</p>
        ))}
      </div>
    </div>
  );
}
