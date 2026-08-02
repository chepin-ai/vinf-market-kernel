import { useEffect, useRef, useState } from 'react';
import type { Bundle, ChainInfo } from '../lib/kernel';
import { verifyChainClient } from '../lib/kernel';

// 内核对话窗: 规则引擎直连状态包(离线可用) + 一键生成LLM上下文简报
interface Msg { who: 'me' | 'kernel'; text: string }

function answer(q: string, b: Bundle): string {
  const s = b.status;
  const norm = q.toLowerCase();
  if (/状态|健康|status|health/.test(q))
    return `链${s.chain.ok ? '✓完整' : '✗断链'} ${s.chain.hops}跳(尾${s.chain.tail}) · 末跳${s.last_tick} · 库${JSON.stringify(s.db)}`;
  if (/心跳|heartbeat/.test(q))
    return `心跳cron 0 9 */3 * *(19f80a04…), Git-first协议: clone→verify→tick→push。末跳${s.last_tick}。失联判据: >4天无tick(看门狗每周日核查)`;
  if (/债|debt/.test(q))
    return '数据债台账:\n' + b.debts.map((d) => `${d.status === 'closed' ? '✓' : '○'} ${d.item}${d.note ? ' — ' + d.note.slice(0, 40) : ''}`).join('\n');
  if (/sorry|队列|未证/.test(q))
    return 'sorry队列:\n' + b.theorems.filter((t) => ['open', 'axiom_candidate'].includes(t.status)).map((t) => `${t.id}[${t.status}] ${t.statement.slice(0, 50)}`).join('\n');
  if (/冲突|矛盾|conflict/.test(q))
    return b.conflicts.length ? `检出${b.conflicts.length}组冲突, 供求证` : '冲突扫描: 0 — 记忆库当前自洽';
  if (/图谱|kg|拓扑|betti|环/.test(norm))
    return `细胞复形: ${b.cell_complex.V}V/${b.cell_complex.E}E/${b.cell_complex.F}F · β₀=${b.cell_complex.betti0} β₁=${b.cell_complex.betti1}${b.cell_complex.cells2.length ? ' · 环: ' + b.cell_complex.cells2[0] : ''}`;
  if (/金融|f\d|vrp|d.?α|alpha/i.test(q))
    return '金融四检:\n' + s.finance.map((f) => '· ' + f).join('\n');
  if (/定理|theorem|T\d+/.test(q)) {
    const m = q.match(/T\d+|SORRY-\w+|AX-\w+|GIBBS-\w+|RENYI-\w+|E\d/i);
    if (m) {
      const t = b.theorems.find((x) => x.id.toUpperCase() === m[0].toUpperCase());
      if (t) return `${t.id} [${t.status}] by ${t.verified_by}\n${t.statement}`;
    }
    return `注册表${b.theorems.length}条: ` + b.theorems.map((t) => t.id).join(', ');
  }
  if (/预测|pred/i.test(q))
    return '开放预测:\n' + b.predictions.map((p) => `${p.id}[${p.status}] ${p.statement.slice(0, 40)}`).join('\n');
  if (/下一步|建议|todo/i.test(q))
    return '建议优先级: ①T31形式化(自然ZKP的extractor攻击) ②F4专项(D3离散度) ③RENYI-MONO从certified升proved(Lean外挂) ④等心跳下一跳验证git-first协议';
  if (/章法|规则|r\d/i.test(norm))
    return b.policy.rules.join('\n');
  return '可问: 状态/心跳/债/sorry/冲突/图谱/金融/定理 T31/预测/章法/下一步。输入"验链"可让我现场重算哈希链。';
}

export default function KernelChat({ bundle }: { bundle: Bundle }) {
  const [msgs, setMsgs] = useState<Msg[]>([
    { who: 'kernel', text: 'v∞ 内核在线。我是规则引擎(离线直连状态包, 判决仍归代码)。问: 状态/心跳/sorry/图谱/金融/下一步…' },
  ]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => { boxRef.current?.scrollTo(0, 99999); }, [msgs]);

  const send = async () => {
    const q = input.trim();
    if (!q) return;
    setInput('');
    setMsgs((m) => [...m, { who: 'me', text: q }]);
    if (/验链|verify/i.test(q)) {
      setBusy(true);
      const v: ChainInfo = await verifyChainClient(bundle.journal);
      setBusy(false);
      setMsgs((m) => [...m, { who: 'kernel', text: v.ok ? `✓ 现场验链通过: ${v.hops}跳重算一致, 尾${v.tail}` : `✗ ${v.detail}` }]);
      return;
    }
    setTimeout(() => setMsgs((m) => [...m, { who: 'kernel', text: answer(q, bundle) }]), 250);
  };

  const brief = () => {
    const s = bundle.status;
    const text = `[v∞内核简报 ${s.ts}] 链${s.chain.ok ? 'OK' : 'BROKEN'} ${s.chain.hops}跳 尾${s.chain.tail}; 末跳${s.last_tick}; 库${JSON.stringify(s.db)}; sorry=${s.sorries.join('/')}; 债务open=${bundle.debts.filter((d) => d.status !== 'closed').map((d) => d.item).join('/') || '无'}; 金融四检=${s.finance.map((f) => f.slice(0, 24)).join(' | ')}。请作为v∞内核的LLM协作者, 基于此状态继续工作(纪律: 你只提案, 代码才判决)。`;
    navigator.clipboard.writeText(text);
    setMsgs((m) => [...m, { who: 'kernel', text: '✓ LLM上下文简报已复制——粘贴到任意LLM会话即把它接入内核回路(人在回路协议)' }]);
  };

  return (
    <div className="flex h-full flex-col">
      <div ref={boxRef} className="h-56 flex-1 space-y-2 overflow-y-auto rounded border border-slate-700/60 bg-slate-950/60 p-2">
        {msgs.map((m, i) => (
          <div key={i} className={`max-w-[92%] rounded p-2 text-[11px] leading-relaxed ${m.who === 'me' ? 'ml-auto bg-cyan-900/40 text-cyan-100' : 'bg-slate-800/70 text-slate-300'}`}>
            <p className="whitespace-pre-wrap font-mono">{m.text}</p>
          </div>
        ))}
        {busy && <p className="font-mono text-[10px] text-slate-500">重算中…</p>}
      </div>
      <div className="mt-2 flex gap-1.5">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && send()}
          placeholder="问内核… (试: T31 / 图谱 / 验链 / 下一步)"
          className="flex-1 rounded border border-slate-600 bg-slate-900 px-2 py-1.5 font-mono text-xs text-slate-200 outline-none placeholder:text-slate-600 focus:border-cyan-500"
        />
        <button onClick={send} className="rounded border border-cyan-500/50 bg-cyan-500/10 px-3 font-mono text-xs text-cyan-300 hover:bg-cyan-500/25">发</button>
        <button onClick={brief} title="生成LLM上下文简报" className="rounded border border-violet-500/50 bg-violet-500/10 px-2 font-mono text-xs text-violet-300 hover:bg-violet-500/25">⇪简报</button>
      </div>
    </div>
  );
}
