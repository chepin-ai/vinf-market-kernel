import { useEffect, useRef, useState } from 'react';
import type { KG } from '../lib/kernel';
import { NODE_COLOR } from '../lib/kernel';

// 轻量力导向布局(无依赖): 知识图谱动态映射
export default function GraphView({ kg }: { kg: KG }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [hover, setHover] = useState<string | null>(null);
  const stateRef = useRef<{ x: number; y: number; vx: number; vy: number }[]>([]);

  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;
    const W = (canvas.width = canvas.offsetWidth * 2);
    const H = (canvas.height = canvas.offsetHeight * 2);
    const N = kg.nodes.length;
    const idx = new Map(kg.nodes.map((n, i) => [n.id, i]));
    if (stateRef.current.length !== N) {
      stateRef.current = kg.nodes.map((_, i) => ({
        x: W / 2 + 260 * Math.cos((i / N) * Math.PI * 2) * (0.4 + Math.random() * 0.6),
        y: H / 2 + 200 * Math.sin((i / N) * Math.PI * 2) * (0.4 + Math.random() * 0.6),
        vx: 0, vy: 0,
      }));
    }
    const pos = stateRef.current;
    let raf = 0;
    let tick = 0;
    const step = () => {
      tick++;
      // 力迭代
      for (let k = 0; k < 3; k++) {
        for (let i = 0; i < N; i++) {
          for (let j = i + 1; j < N; j++) {
            const dx = pos[i].x - pos[j].x, dy = pos[i].y - pos[j].y;
            const d2 = Math.max(dx * dx + dy * dy, 400);
            const f = 9000 / d2;
            pos[i].vx += (dx / Math.sqrt(d2)) * f; pos[i].vy += (dy / Math.sqrt(d2)) * f;
            pos[j].vx -= (dx / Math.sqrt(d2)) * f; pos[j].vy -= (dy / Math.sqrt(d2)) * f;
          }
        }
        for (const e of kg.edges) {
          const a = idx.get(e.src), b = idx.get(e.dst);
          if (a === undefined || b === undefined) continue;
          const dx = pos[b].x - pos[a].x, dy = pos[b].y - pos[a].y;
          const d = Math.max(Math.hypot(dx, dy), 1);
          const f = (d - 150) * 0.012;
          pos[a].vx += (dx / d) * f; pos[a].vy += (dy / d) * f;
          pos[b].vx -= (dx / d) * f; pos[b].vy -= (dy / d) * f;
        }
        for (let i = 0; i < N; i++) {
          pos[i].vx += (W / 2 - pos[i].x) * 0.0015;
          pos[i].vy += (H / 2 - pos[i].y) * 0.0015;
          pos[i].x += pos[i].vx * 0.5; pos[i].y += pos[i].vy * 0.5;
          pos[i].vx *= 0.82; pos[i].vy *= 0.82;
        }
      }
      // 绘制
      ctx.fillStyle = '#0a0f1a';
      ctx.fillRect(0, 0, W, H);
      ctx.strokeStyle = 'rgba(96,165,250,0.28)';
      ctx.lineWidth = 1.5;
      for (const e of kg.edges) {
        const a = idx.get(e.src), b = idx.get(e.dst);
        if (a === undefined || b === undefined) continue;
        ctx.beginPath();
        ctx.moveTo(pos[a].x, pos[a].y);
        ctx.lineTo(pos[b].x, pos[b].y);
        ctx.stroke();
      }
      kg.nodes.forEach((n, i) => {
        const c = NODE_COLOR[n.type] ?? '#94a3b8';
        ctx.beginPath();
        ctx.arc(pos[i].x, pos[i].y, n.type === 'theorem' ? 14 : 10, 0, Math.PI * 2);
        ctx.fillStyle = c + '33';
        ctx.fill();
        ctx.strokeStyle = c;
        ctx.lineWidth = 2;
        ctx.stroke();
        ctx.fillStyle = '#e2e8f0';
        ctx.font = '16px monospace';
        ctx.textAlign = 'center';
        ctx.fillText(n.id.slice(0, 12), pos[i].x, pos[i].y - 18);
      });
      if (tick < 400) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    // hover 命中
    const onMove = (ev: MouseEvent) => {
      const r = canvas.getBoundingClientRect();
      const mx = (ev.clientX - r.left) * 2, my = (ev.clientY - r.top) * 2;
      let best: string | null = null;
      kg.nodes.forEach((n, i) => {
        if (Math.hypot(pos[i].x - mx, pos[i].y - my) < 26) best = `${n.id} · ${n.type} · ${n.status}`;
      });
      setHover(best);
    };
    canvas.addEventListener('mousemove', onMove);
    return () => {
      cancelAnimationFrame(raf);
      canvas.removeEventListener('mousemove', onMove);
    };
  }, [kg]);

  return (
    <div className="relative">
      <canvas ref={ref} className="h-[340px] w-full rounded-lg" />
      {hover && (
        <div className="absolute left-2 top-2 rounded border border-slate-600 bg-slate-900/90 px-2 py-1 font-mono text-xs text-cyan-300">
          {hover}
        </div>
      )}
    </div>
  );
}
