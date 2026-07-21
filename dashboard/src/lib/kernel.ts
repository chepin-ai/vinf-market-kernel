// v∞ OS Dashboard — 数据契约层
// 数据源优先级: GitHub raw(实时) → 本地快照(构建时嵌入)
export const RAW_BASE =
  'https://raw.githubusercontent.com/chepin-ai/vinf-market-kernel/main';

export interface ChainInfo { ok: boolean; hops?: number; tail?: string; detail?: string }
export interface KernelStatus {
  ts: string; chain: ChainInfo; last_tick: string | null;
  db: Record<string, number>; finance: string[]; sorries: string[]; debts: string[];
}
export interface KGNode { id: string; type: string; status: string }
export interface KGEdge { src: string; dst: string; rel: string }
export interface KG { nodes: KGNode[]; edges: KGEdge[]; built: string }
export interface CellComplex { V: number; E: number; F: number; betti0: number; betti1: number; cells2: string[]; chi?: number }
export interface Theorem { id: string; kind: string; statement: string; status: string; verified_by: string; round: number }
export interface Prediction { id: string; statement: string; test_by: string; status: string }
export interface FrontierItem { id: number; finding: string; source: string; round: number }
export interface Debt { id: number; item: string; status: string; note: string }
export interface Proposal { id: string; text: string; parents: string[]; gen: number; fitness: number; novelty: number; status: string }
export interface JournalRec { tick: number; ts: string; actions: string[]; prev_hash: string; hash: string }
export interface Policy { rules: string[]; roles: Record<string, { lane: string; model: string; why: string }>; lanes: Record<string, string>; evidence: Record<string, string> }
export interface Bundle {
  status: KernelStatus; kg: KG; cell_complex: CellComplex; conflicts: unknown[];
  theorems: Theorem[]; predictions: Prediction[]; frontier: FrontierItem[];
  debts: Debt[]; pool: Proposal[]; journal: JournalRec[];
  policy: Policy;
}

export async function loadBundle(): Promise<{ data: Bundle; source: 'github-live' | 'snapshot' }> {
  try {
    const r = await fetch(`${RAW_BASE}/state_bundle.json`, { cache: 'no-store' });
    if (!r.ok) throw new Error(String(r.status));
    return { data: await r.json(), source: 'github-live' };
  } catch {
    const r = await fetch('./state_snapshot.json');
    return { data: await r.json(), source: 'snapshot' };
  }
}

// Python json.dumps(ensure_ascii=False) 的数组分隔符是 ", " —— JS需手工拼接复现
function pyDumpsArr(arr: string[]): string {
  return '[' + arr.map((s) => JSON.stringify(s)).join(', ') + ']';
}

async function sha256hex(text: string): Promise<string> {
  const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return [...new Uint8Array(buf)].map((b) => b.toString(16).padStart(2, '0')).join('');
}

// 浏览器端独立验链: 不信任任何服务器状态, 自己重算(A2′的Web化)
export async function verifyChainClient(journal: JournalRec[]): Promise<ChainInfo> {
  let prev = '0'.repeat(64);
  for (let i = 0; i < journal.length; i++) {
    const rec = journal[i];
    const expect = await sha256hex(prev + pyDumpsArr(rec.actions));
    if (expect !== rec.hash || rec.prev_hash !== prev) {
      return { ok: false, detail: `第${i + 1}跳断链: 期望${expect.slice(0, 12)} 实见${rec.hash.slice(0, 12)}` };
    }
    prev = rec.hash;
  }
  return { ok: true, hops: journal.length, tail: prev.slice(0, 12) };
}

export const STATUS_STYLE: Record<string, string> = {
  established: 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10',
  proved: 'text-emerald-300 border-emerald-400/40 bg-emerald-400/10',
  certified: 'text-teal-300 border-teal-400/40 bg-teal-400/10',
  open: 'text-amber-300 border-amber-400/40 bg-amber-400/10',
  refuted: 'text-rose-400 border-rose-500/40 bg-rose-500/10',
  axiom_candidate: 'text-violet-300 border-violet-400/40 bg-violet-400/10',
  closed: 'text-emerald-400 border-emerald-500/40 bg-emerald-500/10',
};

export const NODE_COLOR: Record<string, string> = {
  theorem: '#34d399', empirical: '#2dd4bf', conditional: '#a78bfa',
  corollary: '#6ee7b7', proposition: '#fbbf24', derived: '#f472b6',
  proposal: '#60a5fa', 'sorry-resolution': '#fb923c',
};
