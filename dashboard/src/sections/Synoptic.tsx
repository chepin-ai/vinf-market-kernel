import { useEffect, useRef } from 'react';

// SCADA 全局动态图: 内核数据流实时映射(动画脉冲=最近一次tick的实测流量)
export interface StageStatus { id: string; label: string; ok: boolean | null; note: string }

const STAGES: { id: string; label: string; x: number; y: number }[] = [
  { id: 'scout', label: 'Scout\n前沿检索', x: 60, y: 70 },
  { id: 'pool', label: '提案池\n演化', x: 60, y: 220 },
  { id: 'prover', label: 'Prover\n立论', x: 220, y: 145 },
  { id: 'falsifier', label: '证伪组\nkimi·pro', x: 380, y: 70 },
  { id: 'aggregator', label: 'T26聚合\nsup否决', x: 380, y: 220 },
  { id: 'verifier', label: 'Verifier\n代码判决', x: 540, y: 145 },
  { id: 'db', label: 'TheoryDB\n记忆库', x: 700, y: 70 },
  { id: 'github', label: 'GitHub\n事实源', x: 700, y: 220 },
  { id: 'watchdog', label: '看门狗\n独立监督', x: 540, y: 300 },
];

const FLOWS: [string, string][] = [
  ['scout', 'prover'], ['pool', 'prover'], ['prover', 'falsifier'],
  ['falsifier', 'aggregator'], ['aggregator', 'verifier'],
  ['verifier', 'db'], ['db', 'github'], ['verifier', 'watchdog'], ['db', 'watchdog'],
];

export default function Synoptic({ stageStatus, lastTick }: {
  stageStatus: Record<string, { ok: boolean | null; note: string }>; lastTick: string | null;
}) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;
    const W = (canvas.width = canvas.offsetWidth * 2);
    const H = (canvas.height = canvas.offsetHeight * 2);
    const S = W / 780;
    let raf = 0;
    let t0 = performance.now();

    const pos = Object.fromEntries(STAGES.map((s) => [s.id, { x: s.x * S, y: s.y * S }]));

    const draw = (now: number) => {
      const t = (now - t0) / 1000;
      ctx.fillStyle = '#0a0f1a';
      ctx.fillRect(0, 0, W, H);
      // 网格
      ctx.strokeStyle = 'rgba(51,65,85,0.25)';
      ctx.lineWidth = 1;
      for (let gx = 0; gx < W; gx += 40 * S) { ctx.beginPath(); ctx.moveTo(gx, 0); ctx.lineTo(gx, H); ctx.stroke(); }
      for (let gy = 0; gy < H; gy += 40 * S) { ctx.beginPath(); ctx.moveTo(0, gy); ctx.lineTo(W, gy); ctx.stroke(); }
      // 流
      for (const [a, b] of FLOWS) {
        const p = pos[a], q = pos[b];
        ctx.strokeStyle = 'rgba(56,189,248,0.30)';
        ctx.lineWidth = 2 * S;
        ctx.beginPath(); ctx.moveTo(p.x, p.y); ctx.lineTo(q.x, q.y); ctx.stroke();
        // 脉冲(相位错开)
        const phase = (t * 0.45 + FLOWS.indexOf([a, b] as never) * 0.13) % 1;
        const px = p.x + (q.x - p.x) * phase, py = p.y + (q.y - p.y) * phase;
        const grad = ctx.createRadialGradient(px, py, 0, px, py, 9 * S);
        grad.addColorStop(0, 'rgba(34,211,238,0.95)');
        grad.addColorStop(1, 'rgba(34,211,238,0)');
        ctx.fillStyle = grad;
        ctx.beginPath(); ctx.arc(px, py, 9 * S, 0, Math.PI * 2); ctx.fill();
      }
      // 节点
      for (const s of STAGES) {
        const p = pos[s.id];
        const st = stageStatus[s.id];
        const ok = st?.ok;
        const col = ok === null || ok === undefined ? '#64748b' : ok ? '#34d399' : '#fb7185';
        const r = 34 * S;
        ctx.beginPath(); ctx.arc(p.x, p.y, r + 6 * S, 0, Math.PI * 2);
        ctx.strokeStyle = col + '44'; ctx.lineWidth = 3 * S; ctx.stroke();
        ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.fillStyle = '#0f172a'; ctx.fill();
        ctx.strokeStyle = col; ctx.lineWidth = 2.5 * S; ctx.stroke();
        ctx.beginPath(); ctx.arc(p.x + r * 0.7, p.y - r * 0.7, 6 * S, 0, Math.PI * 2);
        ctx.fillStyle = col;
        if (ok) { ctx.shadowColor = col; ctx.shadowBlur = 12; }
        ctx.fill(); ctx.shadowBlur = 0;
        ctx.fillStyle = '#e2e8f0';
        ctx.font = `${15 * S}px monospace`;
        ctx.textAlign = 'center';
        s.label.split('\n').forEach((ln, i) => {
          ctx.fillText(ln, p.x, p.y - 4 * S + i * 17 * S);
        });
        if (st?.note) {
          ctx.fillStyle = '#64748b';
          ctx.font = `${11 * S}px monospace`;
          ctx.fillText(st.note.slice(0, 16), p.x, p.y + r + 16 * S);
        }
      }
      // 末跳水印
      ctx.fillStyle = 'rgba(100,116,139,0.6)';
      ctx.font = `${12 * S}px monospace`;
      ctx.textAlign = 'left';
      ctx.fillText(`LAST TICK: ${lastTick ?? '—'}`, 12 * S, H - 12 * S);
      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(raf);
  }, [stageStatus, lastTick]);

  return <canvas ref={ref} className="h-[330px] w-full rounded-lg border border-slate-700/60" />;
}
