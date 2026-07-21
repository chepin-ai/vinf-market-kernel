# -*- coding: utf-8 -*-
"""
v∞ Engine —— 市场ZKP攻击引擎 (分析报告第22-26章的工程实现)
================================================================
总线: ①P构造 → ②Q读取 → ③边缘图 → ④相位钟 → ⑤随机性审计 → ⑥仓位(f***) → ⑦标定(CLV/κ在线)
定理注册: T1-T22 (见报告第27章注册表)
依赖: numpy, scipy, pandas
"""
import numpy as np
from scipy.stats import poisson
from numpy.fft import rfft

# ---------------- ① P构造: Dixon-Coles + γ的U形定律(T11) + 对角加载(K1修正) ----------------
# K1内核修正(Ch.29): γ的真实算子是"对角加载"而非λ缩放——决赛进球不抑制(γ_goal≈1.0)
# 但平局率24%→50%。P构造 = λ缩放(实测γ_goal) × 对角加载L_s
GAMMA_U = {'group':1.00, 'R32':1.00, 'R16':1.07, 'QF':0.86, 'SF':0.89, '3rd':1.51, 'F':1.00}
DIAG_LOAD = {'group':1.0, 'R32':1.0, 'R16':1.51, 'QF':1.71, 'SF':1.14, '3rd':0.46, 'F':3.13}

def diag_load(M, L):
    """对角加载算子: 质量搬向/搬离平局线, 保持E[进球]不变"""
    M2 = M.copy(); idx = np.arange(M.shape[0])
    M2[idx,idx] *= L
    return M2/M2.sum()

def dc_matrix(lh, la, rho=-0.10, mx=12):
    """Dixon-Coles τ修正泊松比分矩阵 (T2的低比分相关性)"""
    M = np.outer([poisson.pmf(i,lh) for i in range(mx)],
                 [poisson.pmf(i,la) for i in range(mx)])
    M[0,0]*=(1-lh*la*rho); M[0,1]*=(1+lh*rho); M[1,0]*=(1+la*rho); M[1,1]*=(1-rho)
    return M/M.sum()

def build_P(lh_raw, la_raw, stage):
    """物理测度P: 原始λ × γ_goal × 对角加载L_stage (K1修正版)"""
    g, L = GAMMA_U[stage], DIAG_LOAD[stage]
    return diag_load(dc_matrix(lh_raw*g, la_raw*g), L), (g, L)

# ---------------- ② Q读取: sup归一化maxitive测度(T8/T13) ----------------
def read_Q(lh_mkt, la_mkt, margin=0.05):
    """市场测度Q: 市场λ(γ盲) + τ + margin; 返回矩阵/1X2/大小球隐含概率"""
    M = dc_matrix(lh_mkt, la_mkt)
    q = {'H':np.tril(M,-1).sum(), 'D':np.trace(M), 'A':np.triu(M,1).sum()}
    q['U25'] = sum(M[i,j] for i in range(3) for j in range(3-i))
    q['O25'] = 1-q['U25']
    return M, q, margin

# ---------------- ③ 边缘图: D_α阶梯 + 逐点Δ(θ) (T12/T13/T16) ----------------
def renyi_ladder(P, Q, alphas=(0.5,1,2,5,np.inf)):
    P = P+1e-12; Q = Q+1e-12
    out = {}
    for a in alphas:
        if a==1: out[a] = (P*np.log(P/Q)).sum()
        elif a==np.inf: out[a] = np.log((P/Q).max())
        else: out[a] = np.log((P**a * Q**(1-a)).sum())/(a-1)
    out['narrative_tax'] = out[np.inf]-out[1]     # T13: 叙事税≥0恒成立
    return out

def edge_map(P, Q, margin=0.05, top=8):
    """逐点信息失衡 Δ(θ)=ln(P/Q)-ln(1/(1-m)): >0 即为可收割状态(T16门槛 p/q>1/(1-m))"""
    D = np.log((P+1e-12)/(Q+1e-12)) + np.log(1-margin)
    idx = np.dstack(np.unravel_index(np.argsort(D.ravel())[::-1], D.shape))[0]
    return [(int(i),int(j),float(D[i,j]),float(P[i,j]/Q[i,j])) for i,j in idx[:top]]

# ---------------- ④ 相位钟: 三通道侧信道(T8侧信道攻击) ----------------
def phase_clock(series, media=None):
    """主信道: 自相关谱(FFT找周期+相位); 校准信道: 媒体量互相关定原点"""
    x = series - series.mean()
    f = np.abs(rfft(x))**2; f[0]=0
    k = np.argmax(f); T = len(x)/k if k>0 else np.inf
    phase = np.angle(rfft(x)[k])
    sig = f.max()/f.mean()
    out = {'period':T, 'phase':phase, 'strength':sig}
    if media is not None:
        c = np.correlate(x, media-media.mean(), 'full')
        out['origin_lag'] = int(np.argmax(c)-(len(x)-1))
    return out

# ---------------- ⑤ 随机性审计电池(T9: TRNG/PRG部门分类) ----------------
def randomness_audit(x):
    import zlib
    x = np.asarray(x, float)
    ac1 = np.corrcoef(x[:-1],x[1:])[0,1]
    f = np.abs(rfft(x-x.mean()))**2; f[0]=0
    spec = f.max()/f.mean()
    comp = len(zlib.compress((x>np.median(x)).astype(np.uint8).tobytes(),9))/len(x)
    prg_score = int(abs(ac1)>0.2) + int(spec>50) + int(comp<0.12)
    return {'ac1':ac1, 'spectral':spec, 'compress':comp,
            'verdict':'PRG(可去随机化)' if prg_score>=2 else 'TRNG(缴凯利税)'}

# ---------------- ⑥ 仓位: f***三约束(T15/T20/T21) ----------------
def size_position(p, q, margin, bankroll, V=None, sigma=0.10, Y=0.7,
                  N_bets=100, discipline=0.5):
    """f*** = min(f*_Kelly, (4/9)Q*/B, ρ*V/B) × discipline
       Q*=V(e/(Yσ))² 冲击容量(T20); ρ*≈10% 隐身容量(T21)"""
    o = (1-margin)/q
    f_k = max((p*o-1)/(o-1), 0)
    e = p*o-1
    caps = {'kelly': f_k}
    if V is not None and e>0:
        Qstar = V*(e/(Y*sigma))**2
        caps['impact'] = 4/9*Qstar/bankroll
        caps['stealth'] = 0.10*V/bankroll
    binding = min(caps, key=caps.get)
    f = caps[binding]*discipline
    return {'f':f, 'stake':f*bankroll, 'binding':binding, 'caps':caps, 'odds':o}

# ---------------- ⑦ 标定: CLV证书 + κ在线辨识 ----------------
def clv_monitor(bets):
    """bets=[(taken,close)]: CLV均值/t值 (w_mkt唯一合法估计器, Ch.21)"""
    x = np.array([np.log(t/c) for t,c in bets])
    t_stat = x.mean()/(x.std()/np.sqrt(len(x))) if len(x)>1 else np.nan
    return {'clv':x.mean(), 't':t_stat, 'lead':'领先' if x.mean()>0 and t_stat>2 else '被追赶?'}

def kappa_online(P_series, Q_series, w=80):
    """滚动OLS κ̂ + CUSUM变点 (Ch.25①: 检测延迟~6拍)"""
    T = len(P_series); kh = np.full(T, np.nan)
    for t in range(w+1, T):
        x = P_series[t-w:t]-Q_series[t-w-1:t-1]; y = np.diff(Q_series[t-w-1:t])
        if (x**2).sum()>1e-8: kh[t] = (x*y).sum()/(x*x).sum()
    return kh

# ---------------- 决胜子模型(加时/点球分解) ----------------
def decider_model(l1, l2, gamma=1.0, pso_h=0.5):
    l1, l2 = l1*gamma, l2*gamma
    r = 30/90*1.06
    Me = np.outer([poisson.pmf(i,l1*r) for i in range(8)],[poisson.pmf(i,l2*r) for i in range(8)])
    et_h, et_d = np.tril(Me,-1).sum(), np.trace(Me)
    M9 = dc_matrix(l1, l2)
    p_h, p_d = np.tril(M9,-1).sum(), np.trace(M9)
    lift = p_h + p_d*(et_h+et_d*pso_h)
    return {'p90':(p_h,p_d,1-p_h-p_d), 'lift_h':lift}
