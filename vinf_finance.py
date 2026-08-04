# -*- coding: utf-8 -*-
"""v∞ 金融引擎（第40章）——理论的主运行域（世界杯已退为历史起源）
四项常驻检验，全部代码判决、结果登记frontier[fin]：
  F1 VRP期限结构(E5复检)   F2 T13金融版(NT≥0命中率)   F3 D_α阶梯sup主导(L7复检)
  F4 D3派生预测(高税市场sup-mean离散度更大, sharpapi面板)
数据刷新：FRED(VIXCLS/SP500, 免钥) → 滚动VRP；本地CSV优先。
"""
import os, json, time, urllib.request
import numpy as np
import pandas as pd

WORK = '/mnt/agents/work/worldcup2026'

def _fred(series, path):
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}'
    try:
        with urllib.request.urlopen(url, timeout=60) as r:
            open(path, 'wb').write(r.read())
        return True
    except Exception:
        return False

class FinanceEngine:
    def __init__(self, db, workdir=WORK):
        self.db, self.wd = db, workdir
        self.results = []

    def F1_vrp_term(self):
        f = os.path.join(self.wd, 'vrp_ladder.csv')
        if not os.path.exists(f): return ('F1', 'skip', 'vrp_ladder.csv缺席')
        v = pd.read_csv(f).sort_values('DTE')
        rho = np.corrcoef(np.argsort(np.argsort(v.DTE)), np.argsort(np.argsort(v.VRP_post)))[0,1]
        long_pos = bool(v.VRP_post.iloc[-1] > 0 and v.VRP_t.iloc[-1] > 2)
        ok = rho > 0.7 and long_pos
        return ('F1', 'pass' if ok else 'fail',
                f'VRP期限秩相关={rho:.2f}, 长端={v.VRP_post.iloc[-1]*100:.2f}点(t={v.VRP_t.iloc[-1]:.1f})')

    def F2_nt_nonneg(self):
        f = os.path.join(self.wd, 'vrp_ladder.csv')
        if not os.path.exists(f): return ('F2', 'skip', '缺数据')
        v = pd.read_csv(f)
        hit = float(v.VRP_hit.mean()); long_hit = float(v[v.DTE>=90].VRP_hit.mean())
        return ('F2', 'pass' if long_hit >= 0.6 else 'fail',
                f'VRP>0命中率: 全期限{hit:.0%}, 长端(≥90d){long_hit:.0%}')

    def F3_dalpha(self):
        f = os.path.join(self.wd, 'dalpha_trimmed.csv')
        if not os.path.exists(f): return ('F3', 'skip', '缺数据')
        t = pd.read_csv(f)
        sup_ratio = float((t.Dinf_t / t.D1_t.replace(0, np.nan)).median())
        mono = bool((t.Dinf_t > t.D1_t).all() and (t.D2_t >= t.D1_t - 1e-9).all())
        return ('F3', 'pass' if (sup_ratio > 2 and mono) else 'fail',
                f'D∞/D1中位={sup_ratio:.1f}×, 阶梯单调={mono}')

    def F4_d3_dispersion(self):
        f = os.path.join(self.wd, 'worldcup_2026_odds_snapshot.csv')
        if not os.path.exists(f):
            # 历史资产已归档(赛事完赛, 快照不回流): 报archived而非skip——不再制造告警噪声
            return ('F4', 'archived', 'sharpapi面板=历史资产(已归档); D3派生检验留待同类面板再现时激活')
        # D3派生(第54章落实): 高协议税市场(player_props/得分手类)逐庄sup-mean离散度 > 低税市场(冠军/胜负/总分)
        d = pd.read_csv(f)
        d = d[d['odds_probability'].between(0.001, 0.999)]
        hi = d.market_type.str.contains('player|scorer|score', case=False, regex=True)
        def disp(g):
            p = g['odds_probability']
            return (p.max() - p.mean()) / max(p.mean(), 1e-9)
        g = d.groupby(['market_type', 'event_id', 'selection'])
        dd = g.filter(lambda x: len(x) >= 3).groupby(['market_type', 'event_id', 'selection']).apply(disp)
        out = pd.DataFrame({'disp': dd})
        out['hi'] = [i[0] for i in out.index]
        out['hi'] = out['hi'].str.contains('player|scorer|score', case=False, regex=True)
        med_hi, med_lo = out[out.hi]['disp'].median(), out[~out.hi]['disp'].median()
        ratio = med_hi / max(med_lo, 1e-9)
        ok = bool(ratio > 1.2 and med_hi > 0)
        return ('F4', 'pass' if ok else 'fail',
                f'高税市场离散度中位={med_hi:.2f} vs 低税={med_lo:.2f} (×{ratio:.1f}) — D3派生{"成立" if ok else "证伪"}')

    def refresh_fred(self):
        """增量刷新VIX/SPX（免钥FRED），供后续tick的VRP滚动检验"""
        ok = 0
        for s, p in [('VIXCLS', 'vix_fred.csv'), ('SP500', 'spx_fred_daily.csv')]:
            ok += _fred(s, os.path.join(self.wd, p))
        return ok

    def run_all(self):
        for fn in [self.F1_vrp_term, self.F2_nt_nonneg, self.F3_dalpha, self.F4_d3_dispersion]:
            fid, verdict, detail = fn()
            self.results.append(dict(fid=fid, verdict=verdict, detail=detail))
            self.db.log('frontier', finding=f'[fin:{fid}] {verdict} — {detail}',
                        source='finance_engine', impact='', round=40)
        return self.results

if __name__ == '__main__':
    import sys
    sys.path.insert(0, WORK)
    import vinf_agents as va
    eng = FinanceEngine(va.TheoryDB(os.path.join(WORK, 'theory_db.sqlite')))
    for r in eng.run_all():
        print(r)
