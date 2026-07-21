# -*- coding: utf-8 -*-
"""
v∞ Data —— v∞ Engine 的数据工程层 (报告第28章)
==================================================
五项剩余数据工程的实现:
 ① odds_feed      赔率流接入 (Polymarket/Kalshi/The Odds API → read_Q)
 ② narrative_heat 叙事热度爬虫 (GDELT → 零模提升事件监控) [已实测上线]
 ③ clv_db         CLV数据库 (SQLite → 领先度三表盘)
 ④ param_cards    分域参数卡 (世界杯/财报季/预测市场/加密)
 ⑤ execution      执行层 (随机化冰山拆单, ρ≤10%隐身纪律)
"""
import json, time, sqlite3, subprocess
import numpy as np

# ==================== ① 赔率流接入 ====================
class PolymarketFeed:
    """Polymarket三API全部公开免key: Gamma(发现)/CLOB(价格簿)/Data(持仓)
    限速: Gamma /markets 300req/10s, 游标分页(禁offset);
    陷阱: outcomes/outcomePrices/clobTokenIds 是字符串化JSON, 需二次json.loads"""
    GAMMA = "https://gamma-api.polymarket.com"
    CLOB  = "https://clob.polymarket.com"
    def _get(self, base, path, **params):
        out = subprocess.run(['curl','-sL','--max-time','20',
            f"{base}{path}?"+'&'.join(f"{k}={v}" for k,v in params.items())],
            capture_output=True, text=True).stdout
        return json.loads(out)
    def discover(self, limit=20, order="volume24hr"):
        """发现活跃市场 → [(question, yes_price, volume, clob_token_ids)]"""
        mkts = self._get(self.GAMMA, "/markets", limit=limit, active="true",
                         order=order, ascending="false")
        res = []
        for m in mkts:
            try:
                prices = json.loads(m["outcomePrices"]); toks = json.loads(m["clobTokenIds"])
                res.append({'q':m['question'], 'yes':float(prices[0]),
                            'vol':float(m.get('volume24hr',0)), 'tokens':toks})
            except Exception: continue
        return res
    def to_read_Q(self, yes_price, overround_adj=True):
        """二元市场: q_yes直接是隐含概率(share price); margin≈spread"""
        return {'yes':yes_price, 'no':1-yes_price}

class KalshiFeed:
    """Kalshi: 单市场orderbook免auth; 批量需RSA签名; demo环境 demo-api.kalshi.co"""
    BASE = "https://api.elections.kalshi.com/trade-api/v2"
    def orderbook(self, ticker, depth=10):
        out = subprocess.run(['curl','-sL','--max-time','20',
            f"{self.BASE}/markets/{ticker}/orderbook?depth={depth}"],
            capture_output=True, text=True).stdout
        return json.loads(out)

class OddsAPIFeed:
    """The Odds API (key制, 免费层500req/月): 体育盘主流庄家赔率 → read_Q"""
    BASE = "https://api.the-odds-api.com/v4"
    def __init__(self, key): self.key = key
    def odds(self, sport, markets="h2h,totals"):
        out = subprocess.run(['curl','-sL','--max-time','20',
            f"{self.BASE}/sports/{sport}/odds?apiKey={self.key}&markets={markets}&regions=eu"],
            capture_output=True, text=True).stdout
        return json.loads(out)

# ==================== ② 叙事热度爬虫 (GDELT, 已实测) ====================
class NarrativeHeat:
    """GDELT 2.0 timelinevol: 免费免key, 限速1次/5秒
    用途: 零模提升事件监控 —— 热度z>2.5 = 叙事破圈 = 零模死亡前兆 = 止盈信号
    实测锚点: Mbappé决赛周热度, 2026-07-19 z=+7.1 (金靴叙事破圈)"""
    URL = "https://api.gdeltproject.org/api/v2/doc/doc"
    def __init__(self, min_interval=6.0): self._last=0; self.min_interval=min_interval
    def heat(self, query, maxrecords=10):
        wait = self.min_interval-(time.time()-self._last)
        if wait>0: time.sleep(wait)
        self._last = time.time()
        out = subprocess.run(['curl','-sL','--max-time','25',
            f"{self.URL}?query={query}&mode=timelinevol&format=json&maxrecords={maxrecords}"],
            capture_output=True, text=True).stdout
        d = json.loads(out)
        pts = d['timeline'][0]['data']
        return [(p['date'][:8], p['value']) for p in pts]
    def promotion_z(self, series, lookback=None):
        """最新点z分数: >2.5 触发提升事件警报"""
        vals = np.array([v for _,v in series])
        base, sd = vals[:-1].mean(), vals[:-1].std()+1e-9
        return (vals[-1]-base)/sd

# ==================== ③ CLV数据库 ====================
class CLVDB:
    """领先度三表盘: ΔLL滚动 / CLV均值+t值 / 提升半衰期"""
    def __init__(self, path='/tmp/clv.db'):
        self.db = sqlite3.connect(path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS bets(
            id INTEGER PRIMARY KEY, ts TEXT, market TEXT, state TEXT,
            p REAL, q_taken REAL, q_close REAL, stake REAL, pnl REAL)""")
        self.db.commit()
    def log(self, ts, market, state, p, q_taken, q_close=None, stake=0, pnl=None):
        self.db.execute("INSERT INTO bets(ts,market,state,p,q_taken,q_close,stake,pnl) VALUES(?,?,?,?,?,?,?,?)",
                        (ts,market,state,p,q_taken,q_close,stake,pnl))
        self.db.commit()
    def dashboard(self):
        rows = self.db.execute("SELECT q_taken,q_close,pnl FROM bets WHERE q_close IS NOT NULL").fetchall()
        if len(rows)<3: return {'status':'样本不足(n<3)'}
        clv = np.array([np.log(t/c) for t,c,_ in rows])
        pnl = np.array([p for _,_,p in rows if p is not None])
        return {'n':len(rows), 'clv_mean':clv.mean(),
                'clv_t':clv.mean()/(clv.std()/np.sqrt(len(clv))),
                'verdict':'领先 ✓' if clv.mean()>0 and clv.mean()/(clv.std()/np.sqrt(len(clv)))>2 else '被追赶警告',
                'pnl_sum':pnl.sum() if len(pnl) else None}

# ==================== ④ 分域参数卡 ====================
PARAM_CARDS = {
 'worldcup':   dict(gamma={'F':0.74,'3rd':1.41,'SF':0.92,'QF':0.89}, margin=0.05,
                    kappa0=0.08, psi0=0.03, tau_ch=1.5, notes='γ的U形(T11); 顶点小球+季军大球'),
 'earnings':   dict(gamma={'low_attn':0.80,'high_attn':1.00}, margin=0.0,
                    kappa0=0.15, psi0=0.05, tau_ch=1.3,
                    notes='PEAD=顶点(w_mkt<1活体); 反γ=新兴/小盘; HFT升κ→衰减中'),
 'prediction': dict(gamma={'tail':0.70,'mid':1.00}, margin=0.02,
                    kappa0=0.20, psi0=0.10, tau_ch=1.6,
                    fees={'kalshi_taker_coef':0.07, 'polymarket_taker':'0.0625*p*(1-p)',
                          'polymarket_maker':0.0, 'arb_window_s':30, 'breakeven_spread_c':3.31},
                    notes='FLB尾端; OI<$50K价格不可信; 跨平台曲率持续数小时; '
                          '2026费率: Kalshi 1-7%阶梯, Polymarket多数市场零费+bundle套利(YES+NO<$1); '
                          '套利窗口2024年5分钟→2026年30秒(κ上升实测); 开源实现: ImMike/polymarket-arbitrage'),
 'crypto':     dict(gamma={'meme_peak':0.85}, margin=0.001,
                    kappa0=0.25, psi0=0.15, tau_ch=1.2,
                    notes='24/7相位=周注意力周期; 平方根冲击成立; meme=税最重'),
}
def param_card(domain): return PARAM_CARDS[domain]

# ==================== ⑤ 执行层: 随机化冰山 ====================
def iceberg_slice(stake, V, rho_max=0.10, n_slices=None, seed=None):
    """随机化拆单(T21隐身纪律): 尺寸~噪声分布, 时序~指数间隔, 校验ρ≤10%
    返回: [(slice_size, delay_seconds)]"""
    rng = np.random.default_rng(seed)
    cap = rho_max*V
    if stake > cap: stake = cap          # 隐身容量硬约束
    n = n_slices or max(3, int(stake/cap*20))
    w = rng.dirichlet(np.ones(n)*2.0)    # 随机尺寸(避免均匀模式被画像)
    sizes = w*stake
    delays = rng.exponential(180., n)    # 指数间隔(泊松到达=最大不可预测)
    from math import erf
    z = (stake/V)*np.sqrt(100)/(1-stake/V)
    det = 0.5*(1+erf((z-1.645)/np.sqrt(2)))   # 侦测率Φ(z-1.645): ρ=10%,N=100 → 29.7%
    return {'slices':list(zip(sizes.round(2), delays.round(0))),
            'rho':stake/V, 'detection_risk':det,
            'stealth':'PASS' if stake/V<=rho_max else 'CAPPED'}

if __name__ == '__main__':
    # 离线自检
    db = CLVDB()
    for i,(t,c) in enumerate([(5.5,4.2),(1.62,1.50),(7.0,5.8),(2.1,1.95),(3.3,2.9)]):
        db.log(f'2026-07-{15+i}','WC2026-F','0-0',0.24,t,c,50,None)
    print('③ CLV仪表盘:', db.dashboard())
    print('④ 参数卡(预测市场):', param_card('prediction')['notes'])
    print('⑤ 冰山拆单:', iceberg_slice(5000, 50000, seed=1))
