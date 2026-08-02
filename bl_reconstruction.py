# -*- coding: utf-8 -*-
import pandas as pd, numpy as np, json, gc
from scipy.interpolate import UnivariateSpline
from scipy.stats import gaussian_kde, spearmanr, mannwhitneyu

COLS = ['QUOTE_DATE','EXPIRE_DATE','DTE','UNDERLYING_LAST','C_IV','P_IV','C_BID','C_ASK','STRIKE']
df = pd.read_csv('/tmp/spyopt/spy_2020_2022.csv', skipinitialspace=True, usecols=lambda c: c.strip().strip('[]') in COLS)
df.columns = [c.strip().strip('[]') for c in df.columns]
for c in ['UNDERLYING_LAST','DTE','C_IV','P_IV','C_BID','C_ASK','STRIKE']:
    df[c] = pd.to_numeric(df[c], errors='coerce').astype('float32')
df['QUOTE_DATE'] = pd.to_datetime(df['QUOTE_DATE'])
df['EXPIRE_DATE'] = pd.to_datetime(df['EXPIRE_DATE'])
print('rows', len(df), 'dates', df.QUOTE_DATE.min().date(), '->', df.QUOTE_DATE.max().date(), flush=True)

S = df.groupby('QUOTE_DATE')['UNDERLYING_LAST'].median().sort_index()
logret = np.log(S).diff()

# ATM IV 面板
d = df[(df.DTE>0)&(df.C_IV>0.01)&(df.C_IV<3)&(df.P_IV>0.01)&(df.P_IV<3)]
d = d.assign(mny=(d.STRIKE-d.UNDERLYING_LAST).abs())
idx = d.groupby(['QUOTE_DATE','EXPIRE_DATE'])['mny'].idxmin()
atm = d.loc[idx, ['QUOTE_DATE','DTE','C_IV','P_IV']].copy()
atm['IV'] = (atm.C_IV+atm.P_IV)/2
del d; gc.collect()
BD = {'~7d':7,'~30d':30,'~60d':60,'~90d':90,'~180d':180}
def bucket(dte):
    for b,h in BD.items():
        lo,hi = {'~7d':(5,12),'~30d':(25,35),'~60d':(55,65),'~90d':(85,95),'~180d':(170,190)}[b]
        if lo<=dte<=hi: return b
atm['bucket'] = atm.DTE.map(bucket); atm = atm.dropna(subset=['bucket'])
rows=[]
for b,h in BD.items():
    sub = atm[atm.bucket==b].groupby('QUOTE_DATE')['IV'].mean()
    rv  = (logret.rolling(h).std()*np.sqrt(252)).reindex(sub.index)
    rvf = (logret.rolling(h).std().shift(-h)*np.sqrt(252)).reindex(sub.index)
    nt, ntf = sub-rv, (sub-rvf).dropna()
    rows.append(dict(bucket=b,DTE=h,n_days=len(sub),IV=float(sub.mean()),RV_trail=float(rv.mean()),
        NT_pre=float(nt.mean()),NT_pre_hit=float((nt>0).mean()),
        VRP_post=float(ntf.mean()),VRP_hit=float((ntf>0).mean()),
        VRP_t=float(ntf.mean()/(ntf.std()/np.sqrt(len(ntf))))))
vrp = pd.DataFrame(rows)
print('\n== T13金融版 VRP阶梯 =='); print(vrp.to_string(index=False))

# 曲面子集: 仅DTE 25-35, 释放主表
surf = df[(df.DTE>=25)&(df.DTE<=35)][['QUOTE_DATE','EXPIRE_DATE','DTE','STRIKE','C_BID','C_ASK','UNDERLYING_LAST']].copy()
del df; gc.collect()
pick = surf.assign(pk=(surf.DTE-30).abs()).sort_values('pk').groupby(['QUOTE_DATE','EXPIRE_DATE']).head(1)
pick['ym'] = pick.QUOTE_DATE.dt.to_period('M')
pick = pick.sort_values('DTE').groupby('ym').head(1)[['QUOTE_DATE','EXPIRE_DATE']]
key = surf.groupby(['QUOTE_DATE','EXPIRE_DATE'])
iv30 = atm[atm.bucket=='~30d'].groupby('QUOTE_DATE')['IV'].mean()
hist30 = np.log(S/S.shift(30))

def bl_density(day, S0):
    cs = day[day.C_BID>0.05].groupby('STRIKE')[['C_BID','C_ASK']].mean()
    if len(cs)<30: return None
    cs['mid']=(cs.C_BID+cs.C_ASK)/2
    cs = cs[(cs.index>S0*0.6)&(cs.index<S0*1.5)]
    if len(cs)<30: return None
    k = np.log(cs.index.values/S0); C = cs.mid.values
    kg = np.linspace(k.min(),k.max(),200)
    spl = UnivariateSpline(k, C, s=len(k)*0.02, k=3)
    Cg = spl(kg); d1 = np.gradient(Cg,kg); d2 = np.gradient(d1,kg)
    K = S0*np.exp(kg); qr = np.maximum((d2-d1)/K,0)   # q_r(k)=q_K*K=(C_kk-C_k)/K
    if np.trapezoid(qr,kg)<=0: return None
    return kg, qr/np.trapezoid(qr,kg)

lad=[]; samples={}
for _, r in pick.iterrows():
    t, exp = r.QUOTE_DATE, r.EXPIRE_DATE
    try: S0 = float(S.loc[t])
    except KeyError: continue
    day = key.get_group((t,exp))
    out = bl_density(day,S0)
    if out is None: continue
    kg,qr = out
    past = hist30.loc[:t].dropna().tail(504)
    if len(past)<120: continue
    pr = np.maximum(gaussian_kde(past.values,bw_method=0.25)(kg),1e-12)
    pr/=np.trapezoid(pr,kg)
    m=(qr>1e-8)&(pr>1e-8)
    if m.sum()<50: continue
    g,q,p = kg[m],qr[m],pr[m]; q/=np.trapezoid(q,g); p/=np.trapezoid(p,g)
    D1=float(np.trapezoid(q*np.log(q/p),g))
    D05=float(2*-np.log(np.trapezoid(np.sqrt(q*p),g)))  # alpha=0.5: -2 ln int sqrt(qp)... = (1/(a-1))ln int q^a p^(1-a)
    D2=float(np.log(np.trapezoid(q*q/p,g)))
    D3=float(np.log(np.trapezoid(q**3/p**2,g))/2)
    Dinf=float(np.max(np.log(q/p)))
    iv=float(iv30.get(t,np.nan))
    lad.append(dict(date=str(t.date()),IV=iv,D05=D05,D1=D1,D2=D2,D3=D3,Dinf=Dinf,steep=Dinf-D1))
    samples[str(t.date())]=(g.tolist(),q.tolist(),p.tolist())
lad=pd.DataFrame(lad); lad['crisis']=lad.IV>0.28
print(f'\n== L7金融版 D_alpha阶梯 n={len(lad)} ==')
print(lad.groupby('crisis')[['D05','D1','D2','D3','Dinf','steep']].median().round(3).to_string())
mono=((lad.D1>=lad.D05-1e-9)&(lad.D2>=lad.D1-1e-9)&(lad.D3>=lad.D2-1e-9)).mean()
print(f'阶梯单调比例 {mono:.3f}')
rho,pv=spearmanr(lad.IV.dropna(),lad.loc[lad.IV.notna(),'steep'])
u=mannwhitneyu(lad[lad.crisis].steep,lad[~lad.crisis].steep,alternative='greater')
print(f'steep~IV spearman rho={rho:.3f} p={pv:.4f}; crisis>calm MWU p={u.pvalue:.4f}')
print(f'IV中位: calm {lad[~lad.crisis].IV.median():.3f} crisis {lad[lad.crisis].IV.median():.3f}')
vrp.to_csv('/tmp/bl/vrp_ladder.csv',index=False); lad.to_csv('/tmp/bl/dalpha_ladder.csv',index=False)
json.dump({k:v for k,v in list(samples.items())},open('/tmp/bl/samples.json','w'))
print('SAVED')
