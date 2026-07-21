import { useEffect, useMemo, useState } from 'react';
import type { Bundle, ChainInfo } from '../lib/kernel';
import { loadBundle, verifyChainClient, STATUS_STYLE } from '../lib/kernel';
import GraphView from '../sections/GraphView';

function Panel({ title, right, children, className = '' }: {
  title: string; right?: React.ReactNode; children: React.ReactNode; className?: string;
}) {
  return (
    <section className={`rounded-xl border border-slate-700/60 bg-slate-900/70 p-4 shadow-lg ${className}`}>
      <header className="mb-3 flex items-center justify-between">
        <h2 className="font-mono text-sm tracking-widest text-cyan-300">{title}</h2>
        {right}
      </header>
      {children}
    </section>
  );
}

function Badge({ s }: { s: string }) {
  return (
    <span className={`inline-block rounded border px-1.5 py-0.5 font-mono text-[10px] ${STATUS_STYLE[s] ?? 'text-slate-300 border-slate-500/40 bg-slate-500/10'}`}>
      {s}
    </span>
  );
}

function Light({ ok, label }: { ok: boolean | null; label: string }) {
  const c = ok === null ? 'bg-slate-500' : ok ? 'bg-emerald-400' : 'bg-rose-500';
  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-xs text-slate-300">
      <span className={`h-2 w-2 rounded-full ${c} ${ok ? 'animate-pulse' : ''}`} />{label}
    </span>
  );
}

export default function Home() {
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [source, setSource] = useState<string>('');
  const [verify, setVerify] = useState<ChainInfo | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [tab, setTab] = useState<'theorems' | 'frontier' | 'policy'>('theorems');

  useEffect(() => {
    loadBundle().then(({ data, source }) => {
      setBundle(data); setSource(source);
    });
  }, []);

  const finParsed = useMemo(() => {
    if (!bundle) return [];
    return bundle.status.finance.map((f) => {
      const m = f.match(/\[fin:(\w+)\]\s*(\w+)\s*—\s*(.*)/);
      return m ? { fid: m[1], verdict: m[2], detail: m[3] } : { fid: '?', verdict: '?', detail: f };
    });
  }, [bundle]);

  if (!bundle) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#070b12] font-mono text-cyan-300">
        v∞ KERNEL BOOTING…
      </div>
    );
  }

  const { status, kg, cell_complex: cc, theorems, frontier, debts, pool, journal, policy, predictions } = bundle;
  const chainOk = status.chain.ok;
  const sorries = theorems.filter((t) => ['open', 'axiom_candidate'].includes(t.status));
  const t31 = theorems.find((t) => t.id === 'T31');

  return (
    <div className="min-h-screen bg-[#070b12] pb-16 text-slate-200">
      {/* ===== 顶栏 ===== */}
      <header className="border-b border-slate-800 bg-slate-950/80 px-6 py-4 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-4">
          <div>
            <h1 className="font-mono text-xl font-bold tracking-wider text-slate-100">
              v∞ <span className="text-cyan-400">OS</span> DASHBOARD
            </h1>
            <p className="font-mono text-[11px] text-slate-500">
              市场理论内核 · 自演化操作系统 · 图形化全局映射
            </p>
          </div>
          <div className="ml-auto flex flex-wrap items-center gap-4">
            <Light ok={chainOk} label={chainOk ? `CHAIN OK · ${status.chain.hops}跳 · ${status.chain.tail}` : 'CHAIN BROKEN'} />
            <Light ok={source === 'github-live'} label={source === 'github-live' ? 'GITHUB LIVE' : 'SNAPSHOT'} />
            <button
              onClick={async () => {
                setVerifying(true);
                setVerify(await verifyChainClient(journal));
                setVerifying(false);
              }}
              className="rounded border border-cyan-500/50 bg-cyan-500/10 px-3 py-1 font-mono text-xs text-cyan-300 transition hover:bg-cyan-500/25"
            >
              {verifying ? '验算中…' : '⟁ 浏览器独立验链'}
            </button>
          </div>
        </div>
        {verify && (
          <div className={`mx-auto mt-2 max-w-7xl font-mono text-xs ${verify.ok ? 'text-emerald-400' : 'text-rose-400'}`}>
            {verify.ok
              ? `✓ 客户端验链通过: ${verify.hops}跳全部重算一致, 尾哈希 ${verify.tail} —— 无需信任任何服务器(A2′的Web化)`
              : `✗ ${verify.detail}`}
          </div>
        )}
      </header>

      <main className="mx-auto mt-6 grid max-w-7xl grid-cols-1 gap-4 px-4 lg:grid-cols-3">
        {/* ===== OS 全局 ===== */}
        <Panel title="◈ OS 全局" className="lg:col-span-1">
          <div className="space-y-2 font-mono text-xs">
            <div className="flex justify-between"><span className="text-slate-500">末次心跳</span><span className="text-slate-200">{status.last_tick ?? '—'}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">状态快照</span><span className="text-slate-200">{status.ts}</span></div>
            <div className="flex justify-between"><span className="text-slate-500">图谱构建</span><span className="text-slate-200">{kg.built}</span></div>
            <hr className="border-slate-800" />
            {Object.entries(status.db).map(([k, v]) => (
              <div key={k} className="flex justify-between">
                <span className="text-slate-500">{k}</span>
                <span className="text-cyan-300">{v}</span>
              </div>
            ))}
          </div>
        </Panel>

        {/* ===== 心跳 / 看门狗 ===== */}
        <Panel title="♥ 心跳 & 看门狗" className="lg:col-span-1">
          <div className="space-y-3">
            <div className="rounded-lg border border-rose-500/30 bg-rose-500/5 p-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-rose-300">自演化心跳</span>
                <Light ok={chainOk} label="active" />
              </div>
              <p className="mt-1 font-mono text-[11px] text-slate-400">cron 0 9 */3 * * · 每3天09:00</p>
              <p className="font-mono text-[10px] text-slate-600">19f80a04-7122-8523-8000-006f6c5e9fd7</p>
              <p className="mt-1 text-[11px] text-slate-500">Git-first: clone→verify→tick→push · KB闭合·sorry消解·池演化·金融四检</p>
            </div>
            <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3">
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs text-amber-300">看门狗(独立监督)</span>
                <Light ok label="watching" />
              </div>
              <p className="mt-1 font-mono text-[11px] text-slate-400">cron 0 9 * * 0 · 每周日09:00</p>
              <p className="font-mono text-[10px] text-slate-600">19f829d1-23f2-84a7-8000-006f1260abf5</p>
              <p className="mt-1 text-[11px] text-slate-500">只查不写: 验链·失联报警(&gt;4天)·行数单调核查</p>
            </div>
            <div className="rounded-lg border border-slate-700 bg-slate-800/40 p-3 font-mono text-[11px] text-slate-400">
              外部事实源: <span className="text-cyan-300">github.com/chepin-ai/vinf-market-kernel</span>
            </div>
          </div>
        </Panel>

        {/* ===== 金融引擎 ===== */}
        <Panel title="▲ 金融引擎四检" className="lg:col-span-1">
          <div className="space-y-2">
            {finParsed.map((f) => (
              <div key={f.fid} className="flex items-start gap-2 rounded border border-slate-700/60 bg-slate-800/40 p-2">
                <Light ok={f.verdict === 'pass' ? true : f.verdict === 'fail' ? false : null} label={f.fid} />
                <span className="font-mono text-[11px] text-slate-300">{f.detail}</span>
              </div>
            ))}
            <p className="pt-1 font-mono text-[10px] text-slate-600">
              F1 VRP期限结构(E5) · F2 T13金融版 · F3 D_α阶梯(L7) · F4 D3派生预测 —— 每次tick自动复检, 判决归代码
            </p>
          </div>
        </Panel>

        {/* ===== 知识图谱 ===== */}
        <Panel
          title="◉ 知识细胞复形"
          right={<span className="font-mono text-[10px] text-slate-500">β₀={cc.betti0} β₁={cc.betti1} · {cc.V}V/{cc.E}E/{cc.F}F{cc.chi !== undefined ? ` · χ=${cc.chi}` : ''}</span>}
          className="lg:col-span-2"
        >
          <GraphView kg={kg} />
          <p className="mt-2 font-mono text-[10px] text-slate-600">
            0-胞=命题 · 1-胞=推演边 · 2-胞=独立环(并行证明路径) · Betti数经GF(2)边界算子计算 —— 代数拓扑化的知识体
          </p>
        </Panel>

        {/* ===== 哈希链时间线 ===== */}
        <Panel title="⛓ 哈希链日志" className="lg:col-span-1">
          <div className="max-h-[340px] space-y-2 overflow-y-auto pr-1">
            {[...journal].reverse().map((r, i) => (
              <div key={i} className="rounded border border-slate-700/60 bg-slate-800/40 p-2">
                <div className="flex items-center justify-between font-mono text-[10px]">
                  <span className="text-slate-500">{r.ts}</span>
                  <span className="text-cyan-400">{r.hash.slice(0, 10)}…</span>
                </div>
                <div className="mt-1 font-mono text-[10px] text-slate-400">
                  {r.actions.slice(0, 3).map((a, j) => <div key={j} className="truncate">· {a}</div>)}
                  {r.actions.length > 3 && <div className="text-slate-600">…+{r.actions.length - 3}</div>}
                </div>
                <div className="mt-1 font-mono text-[9px] text-slate-600">prev: {r.prev_hash.slice(0, 10)}…</div>
              </div>
            ))}
          </div>
        </Panel>

        {/* ===== sorry 队列 ===== */}
        <Panel title="⚗ sorry 消解队列" className="lg:col-span-1">
          <div className="space-y-2">
            {sorries.length === 0 && <p className="font-mono text-xs text-slate-500">队列已清空</p>}
            {sorries.map((t) => (
              <div key={t.id} className="rounded border border-slate-700/60 bg-slate-800/40 p-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-amber-300">{t.id}</span>
                  <Badge s={t.status} />
                  <span className="ml-auto font-mono text-[10px] text-slate-600">{t.verified_by}</span>
                </div>
                <p className="mt-1 text-[11px] leading-relaxed text-slate-400">{t.statement.slice(0, 90)}…</p>
              </div>
            ))}
            {theorems.filter((t) => t.kind === 'sorry-resolution').map((t) => (
              <div key={t.id} className="rounded border border-emerald-700/30 bg-emerald-900/10 p-2">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs text-emerald-300">{t.id}</span>
                  <Badge s={t.status} />
                  <span className="ml-auto font-mono text-[10px] text-slate-600">{t.verified_by}</span>
                </div>
              </div>
            ))}
          </div>
        </Panel>

        {/* ===== 提案池 ===== */}
        <Panel title="❖ 提案池(演化)" className="lg:col-span-1">
          <div className="space-y-2">
            {pool.map((p) => (
              <div key={p.id} className="rounded border border-slate-700/60 bg-slate-800/40 p-2">
                <div className="flex items-center gap-2 font-mono text-[10px]">
                  <span className="text-blue-300">{p.id}</span>
                  <span className="text-slate-500">gen{p.gen}</span>
                  <Badge s={p.status} />
                  <span className="ml-auto text-slate-500">fit {p.fitness}</span>
                </div>
                <div className="mt-1 h-1.5 w-full rounded bg-slate-700">
                  <div className="h-1.5 rounded bg-gradient-to-r from-blue-500 to-cyan-400" style={{ width: `${Math.min(100, (p.fitness + 0.25 * p.novelty) * 100)}%` }} />
                </div>
                <p className="mt-1 text-[11px] text-slate-400">{p.text.slice(0, 70)}</p>
              </div>
            ))}
          </div>
        </Panel>

        {/* ===== 数据债 ===== */}
        <Panel title="▤ 数据债台账" className="lg:col-span-1">
          <div className="space-y-1.5">
            {debts.map((d) => (
              <div key={d.id} className="flex items-center gap-2 font-mono text-[11px]">
                <Light ok={d.status === 'closed'} label="" />
                <span className={d.status === 'closed' ? 'text-slate-500 line-through' : 'text-slate-300'}>{d.item}</span>
                {d.note && <span className="ml-auto truncate text-[10px] text-slate-600">{d.note.slice(0, 26)}</span>}
              </div>
            ))}
          </div>
        </Panel>

        {/* ===== T31 自然ZKP 特设 ===== */}
        {t31 && (
          <Panel title="⟐ 前沿命题 · T31" className="lg:col-span-2 border-violet-500/40">
            <p className="text-[13px] leading-relaxed text-slate-300">
              <span className="text-violet-300">自然即 ZKP 证明系统</span>——自然=零知识 Prover（只泄露现象，不泄露机制）；
              实验=Verifier 的交互挑战；物理理论=简洁论证（简洁性=奥卡姆，soundness=可证伪性，可提取性=机制反演）；
              <span className="text-violet-300">数学&物理前沿突破＝对该证明系统的 extractor 攻击</span>。
            </p>
            <p className="mt-2 font-mono text-[11px] text-pink-300/80">
              └ 派生 D4（T31∧T9 闭合）：最优实验设计＝最大化区分器优势的挑战选择——实验是 T9 的对偶
            </p>
          </Panel>
        )}

        {/* ===== 注册表 / 前沿 / 章法 Tab ===== */}
        <Panel
          title="☰ 注册表"
          right={
            <div className="flex gap-1 font-mono text-[10px]">
              {(['theorems', 'frontier', 'policy'] as const).map((t) => (
                <button key={t} onClick={() => setTab(t)}
                  className={`rounded px-2 py-0.5 ${tab === t ? 'bg-cyan-500/25 text-cyan-200' : 'text-slate-500 hover:text-slate-300'}`}>
                  {t === 'theorems' ? `定理 ${theorems.length}` : t === 'frontier' ? '前沿' : '章法'}
                </button>
              ))}
            </div>
          }
          className="lg:col-span-1"
        >
          <div className="max-h-[300px] space-y-1.5 overflow-y-auto pr-1">
            {tab === 'theorems' && theorems.map((t) => (
              <div key={t.id} className="flex items-center gap-2 font-mono text-[11px]">
                <span className="w-24 truncate text-slate-300">{t.id}</span>
                <Badge s={t.status} />
                <span className="truncate text-[10px] text-slate-500">{t.statement.slice(0, 26)}</span>
              </div>
            ))}
            {tab === 'frontier' && frontier.map((f) => (
              <div key={f.id} className="border-l-2 border-slate-700 pl-2 text-[11px] text-slate-400">
                <span className="font-mono text-[9px] text-slate-600">#{f.id} r{f.round} {f.source}</span>
                <p>{f.finding.slice(0, 90)}</p>
              </div>
            ))}
            {tab === 'policy' && policy.rules.map((r, i) => (
              <p key={i} className="text-[11px] leading-relaxed text-slate-400">{r}</p>
            ))}
          </div>
        </Panel>

        {/* ===== 预测 ===== */}
        <Panel title="◎ 开放预测" className="lg:col-span-1">
          <div className="space-y-1.5">
            {predictions.map((p) => (
              <div key={p.id} className="flex items-center gap-2 font-mono text-[11px]">
                <span className="w-14 text-slate-300">{p.id}</span>
                <Badge s={p.status} />
                <span className="truncate text-[10px] text-slate-500">{p.statement.slice(0, 30)}</span>
              </div>
            ))}
          </div>
        </Panel>
      </main>

      <footer className="mx-auto mt-8 max-w-7xl px-4 text-center font-mono text-[10px] text-slate-600">
        v∞ Market Kernel · A2′/T9: LLM只提案, 代码才判决 · T26: 共识均值池, 否决最大池 ·
        记忆只增不减 · 状态总线: GitHub single-source-of-truth · 本页面即验证者
      </footer>
    </div>
  );
}
