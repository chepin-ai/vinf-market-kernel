# vinf_maxitive.py — v∞ 引擎 maxitive 融合层 (第31-32章)
# 耦合: 原 vinf_engine 的 GAMMA_U(γ) × DIAG_LOAD(L) → MDI 双参数算子 (θ,μ)
#       γ ↔ e^μ (进球轴), L ↔ e^θ (对角轴); LOO 拟合于 jfjelstul 1986+ 男足
import numpy as np, math
from scipy.optimize import fsolve

# ---------- 基础核 ----------
def pois_pmf(l, mx=10):
    i = np.arange(mx+1); f = np.array([math.factorial(x) for x in i])
    return np.exp(-l)*l**i/f

def dc_matrix(lh, la, rho=-0.10, mx=10):
    """Dixon-Coles 比分矩阵 (τ 修正低比分, rho=-0.10 为规则先验)"""
    M = np.outer(pois_pmf(lh,mx), pois_pmf(la,mx))
    tau = {(0,0):1-lh*la*rho, (0,1):1+lh*rho, (1,0):1+la*rho, (1,1):1-rho}
    for (i,j),t in tau.items(): M[i,j] *= t
    return M/M.sum()

II = np.arange(11); DMASK = (II[:,None]==II[None,:]).astype(float); GSUM = II[:,None]+II[None,:]

def mdi_tilt(M, th, mu):
    """T28 MDI 算子: 最小KL stakes形变 M'∝M·exp(θ·1[i=j]+μ·(i+j))
       θ=对角(决胜负)轴=ln L; μ=进球轴≈ln γ。K1对角加载=μ=0截面。"""
    W = M*np.exp(th*DMASK+mu*GSUM); return W/W.sum()

def fit_mdi(M0, d_t, g_t):
    """由目标平局率d_t与进球均值g_t反解(θ,μ) — Csiszár I-投影"""
    th,mu = fsolve(lambda x:[np.trace((W:=M0*np.exp(x[0]*DMASK+x[1]*GSUM))/W.sum())-d_t,
                             np.sum(W/W.sum()*GSUM)-g_t],[0.5,0.0])
    return th, mu

# ---------- maxitive 层 (D15-D17, T23-T27) ----------
def freeze(q):
    """D16 凝固映射 Φ: Δⁿ→Π(Ω), sup归一化 (同胚, 数值验证误差0)"""
    return q/q.max()
def unfreeze(pi):
    """Φ 的逆: π/Σπ"""
    return pi/pi.sum()
def rate_fn(q):
    """D17 隐含速率函数 I_Q=-ln π_Q (Puhalskii桥)"""
    return -np.log(freeze(q))
def renyi(p,q,a):
    if a==1: return np.sum(p*np.log(p/q))
    return np.log(np.sum(p**a*q**(1-a)))/(a-1)
def ladder(p,q):
    """Rényi阶梯 + T23/L7: 返回 (D_1, D_∞, NT, Var/2, 数值斜率)
       L7: ∂D_α/∂α|_{1+} = (1/2)Var_p[ln(p/q)] — 实测292场斜率0.9915"""
    d1 = renyi(p,q,1); dinf = np.max(np.log(p/q))
    V = np.sum(p*(np.log(p/q))**2) - d1**2
    return d1, dinf, dinf-d1, V/2, (renyi(p,q,1.05)-d1)/0.05
def edge_map_rate(P, Q, margin):
    """T25: 边缘 = 速率函数差 + L5门槛 (edge>0 ⟺ p/q>1/(1-m))"""
    return np.log(P/Q) + np.log(1-margin)
def finsler(q, v):
    """T27: maxitive侧无穷小度量 F(q,v)=max v_i/q_i (不对称)"""
    return np.max(v/q)

# ---------- 庄家微观结构 (T26 方向修正版, 第32章) ----------
def bookmaker_disagreement(o_avg, o_max):
    """Max/Avg 分歧度: R_i=(1/o_max_i)/Z_max ÷ (1/o_avg_i)/Z_avg
       注意: Max/Avg测的是分歧(知情签名), 非max-mean信念池化(需Min价或逐庄面板)
       实测: argmin-R状态实现率低于隐含 -3.6pp (淘汰赛-9.3pp) → 站在让价庄一侧"""
    qa = 1/np.asarray(o_avg); qa/=qa.sum(); qm = 1/np.asarray(o_max); qm/=qm.sum()
    return qm/qa
def execution_margins(o_avg, o_max):
    """执行层协议税: 实测 Avg=4.92% vs Max=-0.39% (跨庄最优价打穿margin)"""
    return (1/np.asarray(o_avg)).sum()-1, (1/np.asarray(o_max)).sum()-1

# ---------- LOO MDI 阶段参数协议 (无未来函数) ----------
def loo_mdi_params(jfm3, exclude_year=None, stages=('R16','QF','SF','3rd','F')):
    """jfm3: jfjelstul 1986+男足, 需含 stg/d90/g90 列 (90'基准, Laplace平滑)"""
    d = jfm3 if exclude_year is None else jfm3[jfm3.year!=exclude_year]
    M0 = dc_matrix(d.home_team_score.mean(), d.away_team_score.mean())
    prm = {}
    for s in stages:
        sub = d[d.stg==s]; n = len(sub)
        th, mu = fit_mdi(M0, (sub.d90.sum()+1)/(n+2), sub.g90.mean())
        prm[s] = dict(th=th, mu=mu, n=n)
    prm['R32'] = dict(prm['R16']); prm['R32']['n'] = 0   # R32无历史→R16代理
    prm['group'] = dict(th=0.0, mu=0.0, n=-1)
    return prm

# ---------- 主接口: 单场 1X2 ----------
def predict_1x2(lh, la, th, mu, o_avg, rho=-0.10):
    """融合引擎单场: MDI(θ,μ) × DC → P; Avg赔率 → Q; 返回全诊断"""
    M = mdi_tilt(dc_matrix(lh,la,rho), th, mu)
    P = np.array([np.tril(M,-1).sum(), np.trace(M), np.triu(M,1).sum()]); P/=P.sum()
    Q = 1/np.asarray(o_avg); Q /= Q.sum(); m = (1/np.asarray(o_avg)).sum()-1
    d1, dinf, nt, v2, slope = ladder(P, Q)
    edge = edge_map_rate(P, Q, m)
    return dict(P=P, Q=Q, margin=m, D1=d1, Dinf=dinf, NT=nt, V2=v2, L7slope=slope,
                edge=edge, vertex=int(np.argmax(edge)),
                I_P=rate_fn(P), I_Q=rate_fn(Q))
