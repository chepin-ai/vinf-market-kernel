# backtest_real_2014_2026.py — 全量真实数据回测 (football-data WorldCup2026.xlsx)
# 292场 (2014/2018/2022/2026, 2场2026半决赛赔率缺失剔除), 无未来函数协议
# 依赖: pandas, numpy, scipy, openpyxl; 数据: wc2026.xlsx + jfjelstul CSV
import pandas as pd, numpy as np, math, collections
from vinf_maxitive import (dc_matrix, mdi_tilt, fit_mdi, ladder, freeze, rate_fn,
                           edge_map_rate, loo_mdi_params)

XLSX = 'wc2026.xlsx'; JF = 'historical_matches_1930_2022.csv'

def load_wc(sheet, year):
    d = pd.read_excel(XLSX, sheet_name=sheet).sort_values('Date').reset_index(drop=True)
    out = pd.DataFrame({'year':year,'home':d['Home'],'away':d['Away'],
        'date':pd.to_datetime(d['Date']),'hg':d['HGFT'],'ag':d['AGFT'],
        'oH':d['H-Avg'],'oD':d['D-Avg'],'oA':d['A-Avg'],
        'mH':d['H-Max'],'mD':d['D-Max'],'mA':d['A-Max']})
    n_group = 48 if year!=2026 else 72
    ko = (['R16']*8+['QF']*4+['SF']*2+['3rd']+['F']) if year!=2026 else (['R32']*16+['R16']*8+['QF']*4+['SF']*2)
    out['stage'] = ['group']*n_group + ko[:len(out)-n_group]
    return out

jf = pd.read_csv(JF)
jf['year'] = jf['tournament_name'].str.extract(r'(\d{4})').astype(int)
def norm_stage(s):
    s=str(s)
    if 'round of 16' in s: return 'R16'
    if 'quarter' in s: return 'QF'
    if 'semi' in s: return 'SF'
    if 'third' in s: return '3rd'
    if s=='final': return 'F'
jf['stg'] = jf.stage_name.map(norm_stage)
jfm3 = jf[(jf.year>=1986)&(jf.year%4==2)&jf.stg.notna()].copy()  # 男足1986+
jfm3['d90'] = (jfm3.home_team_score==jfm3.away_team_score)|jfm3.extra_time|jfm3.penalty_shootout
jfm3['g90'] = jfm3.home_team_score+jfm3.away_team_score-0.3*(jfm3.extra_time|jfm3.penalty_shootout)

ALL = pd.concat([load_wc('WorldCup2014',2014),load_wc('WorldCup2018',2018),
                 load_wc('WorldCup2022',2022),load_wc('WorldCup2026',2026)],ignore_index=True)
ALL = ALL.dropna(subset=['oH','oD','oA','mH','mD','mA']).reset_index(drop=True)

def run(ALL, k=2.0, hfa=1.06, mu0=1.32):
    recs=[]
    for year in sorted(ALL.year.unique()):
        prm = loo_mdi_params(jfm3, None if year==2026 else year)
        sub = ALL[ALL.year==year].sort_values('date').reset_index(drop=True)
        gf,ga,npl = {},{},{}
        for _,r in sub.iterrows():
            h,a=r.home,r.away
            mu_t = mu0 if len(gf)<4 else sum(gf.values())/max(sum(npl.values()),1)
            lam = lambda t,o: mu_t*((gf.get(t,0)+k*mu_t)/((npl.get(t,0)+k)*mu_t))*((ga.get(o,0)+k*mu_t)/((npl.get(o,0)+k)*mu_t))
            lh,la = lam(h,a)*hfa, lam(a,h)/hfa
            st = prm[r.stage]
            M = mdi_tilt(dc_matrix(lh,la), st['th'], st['mu'])
            P = np.array([np.tril(M,-1).sum(),np.trace(M),np.triu(M,1).sum()]); P/=P.sum()
            oa = np.array([r.oH,r.oD,r.oA]); om = np.array([r.mH,r.mD,r.mA])
            Q = 1/oa; Q/=Q.sum(); m=(1/oa).sum()-1
            d1,dinf,nt,v2,slope = ladder(P,Q)
            edge = edge_map_rate(P,Q,m); vtx=int(np.argmax(edge))
            y = 0 if r.hg>r.ag else (1 if r.hg==r.ag else 2)
            recs.append(dict(year=year,stage=r.stage,home=h,away=a,P=P,Q=Q,edge=edge,
                             vtx=vtx,y=y,o_exec=om,o_avg=oa,d1=d1,dinf=dinf,nt=nt,v2=v2,slope=slope,margin=m))
            gf[h]=gf.get(h,0)+r.hg; ga[h]=ga.get(h,0)+r.ag; npl[h]=npl.get(h,0)+1
            gf[a]=gf.get(a,0)+r.ag; ga[a]=ga.get(a,0)+r.hg; npl[a]=npl.get(a,0)+1
    return recs

if __name__ == '__main__':
    R = run(ALL)
    sl=np.array([r['slope'] for r in R]); v2=np.array([r['v2'] for r in R]); nts=np.array([r['nt'] for r in R])
    print(f"L7: corr={np.corrcoef(sl,v2)[0,1]:.4f} slope={np.polyfit(v2,sl,1)[0]:.4f}")
    print(f"T13: NT>=0 {(nts>=-1e-12).mean()*100:.1f}%  NT均值={nts.mean():.4f}")
    llP=np.mean([-np.log(r['P'][r['y']]) for r in R]); llQ=np.mean([-np.log(r['Q'][r['y']]) for r in R])
    print(f"校准: logloss P={llP:.4f} Q={llQ:.4f}")
    KO=[r for r in R if r['stage']!='group']
    S1=[dict(win=r['y']==r['vtx'],o=r['o_exec'][r['vtx']]) for r in KO if r['edge'][r['vtx']]>0]
    print(f"S1顶点(KO): n={len(S1)} ROI={sum((b['o']-1) if b['win'] else -1 for b in S1)/len(S1)*100:+.2f}%")
    mA=np.mean([(1/r['o_avg']).sum()-1 for r in R]); mM=np.mean([(1/r['o_exec']).sum()-1 for r in R])
    print(f"执行层: Avg margin={mA*100:.2f}% Max margin={mM*100:.2f}%")
