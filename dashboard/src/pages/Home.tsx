import { useEffect, useMemo, useState } from 'react';
import type { Bundle, ChainInfo } from '../lib/kernel';
import { loadBundle, verifyChainClient, STATUS_STYLE } from '../lib/kernel';
import GraphView from '../sections/GraphView';
import Synoptic from '../sections/Synoptic';
import ControlDeck from '../sections/ControlDeck';
import KernelChat from '../sections/KernelChat';
import SwarmView from '../sections/SwarmView';
import ProverBoard from '../sections/ProverBoard';
import FinanceBoard from '../sections/FinanceBoard';
import Alerts, { computeAlerts } from '../sections/Alerts';

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

function Light({ ok, label }: { ok: boolean | null; label: string }) {
  const c = ok === null ? 'bg-slate-500' : ok ? 'bg-emerald-400' : 'bg-rose-500';
  return (
    <span className="inline-flex items-center gap-1.5 font-mono text-xs text-slate-300">
      <span className={`h-2 w-2 rounded-full ${c} ${ok ? 'animate-pulse' : ''}`} />{label}
    </span>
  );
}

const TABS = ['金融', '蜂群', '证明引擎', '细胞复形', '哈希链', '自*志', '全景·边界', '注册表'] as const;

const KIND_COLOR: Record<string, string> = {
  自修正: '#fbbf24', 自证伪: '#fb7185', 自修复: '#34d399', 自纠错: '#2dd4bf',
  自完善: '#60a5fa', 自适应: '#a78bfa', 自演化: '#f472b6', 自监督: '#fb923c',
};

export default function Home() {
  const [bundle, setBundle] = useState<Bundle | null>(null);
  const [source, setSource] = useState('');
  const [verify, setVerify] = useState<ChainInfo | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [tab, setTab] = useState<(typeof TABS)[number]>('金融');
  const [tickAgo, setTickAgo] = useState('');
  const [selNode, setSelNode] = useState<string | null>(null);

  useEffect(() => {
    const load = () => loadBundle().then(({ data, source }) => { setBundle(data); setSource(source); });
    load();
    const iv = setInterval(load, 120000); // 2分钟自动刷新(SCADA心跳)
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    if (!bundle?.status.last_tick) return;
    const f = () => {
      const d = Date.now() - new Date(bundle.status.last_tick!.replace(' ', 'T')).getTime();
      const h = Math.floor(d / 36e5), m = Math.floor((d % 36e5) / 6e4);
      setTickAgo(h > 0 ? `${h}小时${m}分前` : `${m}分前`);
    };
    f();
    const iv = setInterval(f, 30000);
    return () => clearInterval(iv);
  }, [bundle]);

  const alerts = useMemo(() => (bundle ? computeAlerts(bundle, source) : []), [bundle, source]);

  if (!bundle) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#070b12] font-mono text-cyan-300">
        v∞ KERNEL BOOTING…
      </div>
    );
  }

  const { status, kg, cell_complex: cc, theorems, frontier, debts, pool, journal } = bundle;
  const chainOk = status.chain.ok;
  const stageStatus = {
    scout: { ok: true, note: 'kimi/$web' },
    pool: { ok: pool.some((p) => p.status === 'open') || pool.length > 0, note: `${pool.length}提案` },
    prover: { ok: true, note: 'pro泳道' },
    falsifier: { ok: true, note: 'kimi+pro异构' },
    aggregator: { ok: true, note: 'sup否决' },
    verifier: { ok: chainOk, note: '代码判决' },
    db: { ok: true, note: Object.values(status.db).reduce((a, b) => a + b, 0) + '行' },
    github: { ok: source === 'github-live', note: source === 'github-live' ? 'LIVE' : '降级' },
    watchdog: { ok: true, note: '每周日' },
  };
  const finLights = status.finance.map((f) => {
    const m = f.match(/\[fin:(\w+)\]\s*(\w+)/);
    return { fid: m?.[1] ?? '?', verdict: m?.[2] ?? '?' };
  });

  return (
    <div className="min-h-screen bg-[#070b12] pb-12 text-slate-200">
      {/* ===== SCADA 顶栏 ===== */}
      <header className="border-b border-slate-800 bg-slate-950/85 px-5 py-3 backdrop-blur">
        <div className="mx-auto flex max-w-[1500px] flex-wrap items-center gap-x-5 gap-y-2">
          <div>
            <h1 className="font-mono text-lg font-bold tracking-wider text-slate-100">
              v∞ <span className="text-cyan-400">SCADA</span> 内核控制台
            </h1>
            <p className="font-mono text-[10px] text-slate-500">自演化理论机器 · 工控级全局映射 · 人在回路</p>
          </div>
          <Light ok={chainOk} label={chainOk ? `CHAIN ${status.chain.hops}跳·${status.chain.tail}` : 'BROKEN'} />
          <Light ok={source === 'github-live'} label={source === 'github-live' ? 'LIVE' : 'SNAPSHOT'} />
          <Light ok={alerts.filter((a) => a.sev === 'crit').length === 0} label={`告警 ${alerts.length}`} />
          <span className="font-mono text-[11px] text-slate-400">末跳 {tickAgo || status.last_tick}</span>
          <button
            onClick={async () => { setVerifying(true); setVerify(await verifyChainClient(journal)); setVerifying(false); }}
            className="ml-auto rounded border border-cyan-500/50 bg-cyan-500/10 px-3 py-1 font-mono text-xs text-cyan-300 hover:bg-cyan-500/25"
          >
            {verifying ? '验算中…' : '⟁ 独立验链'}
          </button>
        </div>
        {verify && (
          <div className={`mx-auto mt-1.5 max-w-[1500px] font-mono text-xs ${verify.ok ? 'text-emerald-400' : 'text-rose-400'}`}>
            {verify.ok ? `✓ 客户端验链通过: ${verify.hops}跳重算一致(尾${verify.tail})` : `✗ ${verify.detail}`}
          </div>
        )}
      </header>

      <main className="mx-auto mt-4 max-w-[1500px] space-y-4 px-4">
        {/* ===== 行1: 全局动态图 + 控制台 ===== */}
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
          <Panel title="◈ OS 全局实时动态" className="xl:col-span-2"
            right={<span className="font-mono text-[10px] text-slate-500">脉冲=数据流 · 灯=机制健康</span>}>
            <Synoptic stageStatus={stageStatus} lastTick={status.last_tick} />
            <div className="mt-2 grid grid-cols-3 gap-2 font-mono text-[10px] md:grid-cols-6">
              {Object.entries(status.db).map(([k, v]) => (
                <div key={k} className="rounded bg-slate-800/60 px-2 py-1 text-center">
                  <span className="text-slate-500">{k}</span> <span className="text-cyan-300">{v}</span>
                </div>
              ))}
              <div className="rounded bg-slate-800/60 px-2 py-1 text-center">
                <span className="text-slate-500">kg</span> <span className="text-cyan-300">{kg.nodes.length}N/{kg.edges.length}E</span>
              </div>
            </div>
          </Panel>
          <Panel title="⚙ 即时控制 · 动态调参">
            <ControlDeck bundle={bundle} />
          </Panel>
        </div>

        {/* ===== 行2: 告警 + 对话窗 + 心跳/看门狗/金融 ===== */}
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <Panel title="⚠ 告警 · 即时响应" className="lg:col-span-1">
            <Alerts alerts={alerts} />
          </Panel>
          <Panel title="✉ 内核对话窗" className="lg:col-span-1">
            <KernelChat bundle={bundle} />
          </Panel>
          <Panel title="♥ 心跳·看门狗·金融四检" className="lg:col-span-1">
            <div className="space-y-2 font-mono text-[11px]">
              <div className="rounded border border-rose-500/30 bg-rose-500/5 p-2">
                <div className="flex justify-between"><span className="text-rose-300">自演化心跳</span><Light ok={chainOk} label="active" /></div>
                <p className="text-[10px] text-slate-500">0 9 */3 * * · Git-first · 19f80a04…</p>
              </div>
              <div className="rounded border border-amber-500/30 bg-amber-500/5 p-2">
                <div className="flex justify-between"><span className="text-amber-300">看门狗</span><Light ok label="watching" /></div>
                <p className="text-[10px] text-slate-500">0 9 * * 0 · 只查不写 · 19f829d1…</p>
              </div>
              <div className="grid grid-cols-4 gap-1.5 pt-1">
                {finLights.map((f) => (
                  <div key={f.fid} className="rounded border border-slate-700/60 bg-slate-800/40 p-1.5 text-center">
                    <Light ok={f.verdict === 'pass' ? true : f.verdict === 'fail' ? false : null} label={f.fid} />
                  </div>
                ))}
              </div>
              <p className="text-[9px] text-slate-600">F1 VRP期限(E5) · F2 T13金融版 · F3 D_α阶梯(L7) · F4 D3派生</p>
            </div>
          </Panel>
        </div>

        {/* ===== 行3: 大视图页签 ===== */}
        <Panel
          title="☰ 机制深潜"
          right={
            <div className="flex gap-1 font-mono text-[10px]">
              {TABS.map((t) => (
                <button key={t} onClick={() => setTab(t)}
                  className={`rounded px-2.5 py-1 ${tab === t ? 'bg-cyan-500/25 text-cyan-200' : 'text-slate-500 hover:text-slate-300'}`}>
                  {t}
                </button>
              ))}
            </div>
          }
        >
          {tab === '金融' && <FinanceBoard bundle={bundle} />}
          {tab === '蜂群' && <SwarmView bundle={bundle} />}
          {tab === '证明引擎' && <ProverBoard bundle={bundle} />}
          {tab === '细胞复形' && (
            <div>
              <GraphView kg={kg} onSelect={setSelNode} selected={selNode} />
              {selNode && (
                <div className="mt-2 rounded border border-cyan-500/40 bg-cyan-500/5 p-2">
                  {(() => {
                    const t = theorems.find((x) => x.id === selNode);
                    const p = pool.find((x) => x.id === selNode);
                    const rel = kg.edges.filter((e) => e.src === selNode || e.dst === selNode);
                    return (
                      <>
                        <div className="flex items-center gap-2 font-mono text-xs">
                          <span className="text-cyan-300">{selNode}</span>
                          {t && <span className={`rounded border px-1.5 py-0.5 text-[10px] ${STATUS_STYLE[t.status] ?? ''}`}>{t.status}</span>}
                          <button onClick={() => setSelNode(null)} className="ml-auto text-slate-500 hover:text-slate-300">✕</button>
                        </div>
                        {t && <p className="mt-1 text-[11px] text-slate-400">{t.statement}</p>}
                        {t && <p className="mt-0.5 font-mono text-[10px] text-slate-600">verified_by: {t.verified_by} · round {t.round}</p>}
                        {p && <p className="mt-1 text-[11px] text-slate-400">{p.text} · fit {p.fitness} · gen{p.gen}</p>}
                        <p className="mt-1 font-mono text-[10px] text-slate-500">
                          关联{rel.length}条: {rel.slice(0, 5).map((e) => `${e.src}→${e.dst}`).join(' · ')}
                        </p>
                      </>
                    );
                  })()}
                </div>
              )}
              <p className="mt-2 font-mono text-[10px] text-slate-600">
                点击节点查看详情/关联 · β₀={cc.betti0} β₁={cc.betti1} · {cc.V}V/{cc.E}E/{cc.F}F{cc.chi !== undefined ? ` · χ=${cc.chi}` : ''} ·
                环: {cc.cells2.slice(0, 3).join(' / ') || '无'}
              </p>
            </div>
          )}
          {tab === '哈希链' && (
            <div className="grid max-h-[320px] grid-cols-1 gap-2 overflow-y-auto md:grid-cols-2">
              {[...journal].reverse().map((r, i) => (
                <div key={i} className="rounded border border-slate-700/60 bg-slate-800/40 p-2">
                  <div className="flex justify-between font-mono text-[10px]">
                    <span className="text-slate-500">{r.ts}</span>
                    <span className="text-cyan-400">{r.hash.slice(0, 12)}…</span>
                  </div>
                  <div className="mt-1 font-mono text-[10px] text-slate-400">
                    {r.actions.map((a, j) => <div key={j} className="truncate">· {a}</div>)}
                  </div>
                  <div className="mt-1 font-mono text-[9px] text-slate-600">prev {r.prev_hash.slice(0, 12)}…</div>
                </div>
              ))}
            </div>
          )}
          {tab === '自*志' && (
            <div className="space-y-1.5">
              {(bundle.self_events ?? []).map((e, i) => (
                <div key={i} className="flex items-start gap-2 rounded border border-slate-700/50 bg-slate-900/50 p-2">
                  <span className="mt-0.5 rounded border px-1.5 py-0.5 font-mono text-[10px]"
                    style={{ color: KIND_COLOR[e.kind] ?? '#94a3b8', borderColor: (KIND_COLOR[e.kind] ?? '#94a3b8') + '55' }}>
                    {e.kind}
                  </span>
                  <div>
                    <p className="text-[11px] leading-relaxed text-slate-300">{e.event}</p>
                    <p className="font-mono text-[9px] text-slate-600">round {e.round}</p>
                  </div>
                </div>
              ))}
              <p className="font-mono text-[10px] text-slate-600">引擎自*动态实录: 每一次自我修正/证伪/修复都留痕——这是自演化的审计轨</p>
            </div>
          )}
          {tab === '全景·边界' && (
            <div className="grid grid-cols-1 gap-3 md:grid-cols-3">
              <div>
                <p className="mb-1.5 font-mono text-[10px] tracking-widest text-emerald-400">已建立 (幸存清单)</p>
                {theorems.filter((t) => ['established', 'proved', 'certified'].includes(t.status)).map((t) => (
                  <p key={t.id} className="border-l-2 border-emerald-500/50 pl-2 font-mono text-[10px] leading-relaxed text-slate-400">
                    <span className="text-emerald-300">{t.id}</span> {t.statement.slice(0, 44)}
                  </p>
                ))}
              </div>
              <div>
                <p className="mb-1.5 font-mono text-[10px] tracking-widest text-rose-400">已证伪 (阵亡清单)</p>
                {theorems.filter((t) => t.status === 'refuted').map((t) => (
                  <p key={t.id} className="border-l-2 border-rose-500/50 pl-2 font-mono text-[10px] leading-relaxed text-slate-400">
                    <span className="text-rose-300">{t.id}</span> {t.statement.slice(0, 44)}
                  </p>
                ))}
                {bundle.predictions.filter((p) => p.status === 'refuted').map((p) => (
                  <p key={p.id} className="border-l-2 border-rose-500/50 pl-2 font-mono text-[10px] leading-relaxed text-slate-400">
                    <span className="text-rose-300">{p.id}</span> {p.statement.slice(0, 44)}
                  </p>
                ))}
                <p className="mt-2 font-mono text-[9px] text-slate-600">阵亡与幸存同等珍贵——证伪是理论的边界刻刀</p>
              </div>
              <div>
                <p className="mb-1.5 font-mono text-[10px] tracking-widest text-amber-400">开放边界 (理论不主张的)</p>
                {theorems.filter((t) => ['open', 'axiom_candidate'].includes(t.status)).map((t) => (
                  <p key={t.id} className="border-l-2 border-amber-500/50 pl-2 font-mono text-[10px] leading-relaxed text-slate-400">
                    <span className="text-amber-300">{t.id}</span>[{t.status}] {t.statement.slice(0, 40)}
                  </p>
                ))}
                {bundle.predictions.filter((p) => p.status === 'open').map((p) => (
                  <p key={p.id} className="border-l-2 border-amber-500/50 pl-2 font-mono text-[10px] leading-relaxed text-slate-400">
                    <span className="text-amber-300">{p.id}</span> {p.statement.slice(0, 40)}
                  </p>
                ))}
              </div>
            </div>
          )}
          {tab === '注册表' && (
            <div className="grid max-h-[320px] grid-cols-1 gap-x-6 gap-y-1 overflow-y-auto md:grid-cols-2">
              {theorems.map((t) => (
                <div key={t.id} className="flex items-center gap-2 font-mono text-[11px]">
                  <span className="w-28 truncate text-slate-300">{t.id}</span>
                  <span className={`rounded border px-1.5 py-0.5 text-[10px] ${STATUS_STYLE[t.status] ?? ''}`}>{t.status}</span>
                  <span className="truncate text-[10px] text-slate-500">{t.statement.slice(0, 34)}</span>
                </div>
              ))}
              {frontier.slice(0, 10).map((f) => (
                <div key={`f${f.id}`} className="col-span-1 border-l border-slate-700 pl-2 font-mono text-[10px] text-slate-500">
                  #{f.id} {f.finding.slice(0, 60)}
                </div>
              ))}
              {debts.map((d) => (
                <div key={`d${d.id}`} className="flex items-center gap-2 font-mono text-[10px] text-slate-500">
                  <span className={d.status === 'closed' ? 'text-emerald-500' : 'text-amber-400'}>{d.status === 'closed' ? '✓' : '○'}</span>
                  <span>{d.item}</span>
                </div>
              ))}
            </div>
          )}
        </Panel>
      </main>

      <footer className="mx-auto mt-6 max-w-[1500px] px-4 text-center font-mono text-[10px] text-slate-600">
        v∞ Market Kernel SCADA · A2′/T9 代码判决 · T26 sup否决 · 人在回路=root权限 · 每120s自动刷新 · 本页面即验证者
      </footer>
    </div>
  );
}
