# -*- coding: utf-8 -*-
"""v∞ 多市场态势感知引擎 (第48章) — 中国/香港/美国 全市场实时联动
数据源链: Yahoo(query1/query2) → FRED(仅美股系列) → 本地CSV兜底(随Git追踪, 冷启动可用)。
产物: market_pulse.json — 资产快照 + 跨市场信号 + 内核意见; 供 CI、Dashboard、策略引擎共用。
"""
import os, json, time, urllib.request, io
import numpy as np
import pandas as pd

WORK = os.path.dirname(os.path.abspath(__file__))
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36'}

ASSETS = {
    'CN300':  dict(name='沪深300',   market='CN', local='csi300.csv',     yahoo='000300.SS', fred=None),
    'CNSH':   dict(name='上证综指',   market='CN', local='shcomp.csv',     yahoo='000001.SS', fred=None),
    'HK':     dict(name='腾讯(港股代理)', market='HK', local='tencent_hk.csv', yahoo='0700.HK', fred=None),
    'HSI':    dict(name='恒生指数',   market='HK', local='hsi.csv',        yahoo='^HSI',     fred=None),
    'SPX':    dict(name='标普500',   market='US', local='spx_fred.csv',   yahoo='^GSPC',    fred='SP500'),
    'VIX':    dict(name='VIX',      market='US', local='vix_hist.csv',   yahoo='^VIX',     fred='VIXCLS'),
    'US10Y':  dict(name='美债10Y',  market='US', local='us10y.csv',      yahoo='^TNX',     fred='DGS10'),
}


def _yahoo(sym):
    for host in ('query1.finance.yahoo.com', 'query2.finance.yahoo.com'):
        try:
            url = f'https://{host}/v8/finance/chart/{sym}?range=6mo&interval=1d'
            raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=45).read().decode()
            r = json.loads(raw)['chart']['result'][0]
            ts, cl = r['timestamp'], r['indicators']['quote'][0]['close']
            d = pd.DataFrame({'d': pd.to_datetime(ts, unit='s').normalize(), 's': cl}).dropna()
            return d
        except Exception:
            continue
    return None


def _fred(series):
    url = f'https://fred.stlouisfed.org/graph/fredgraph.csv?id={series}'
    raw = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60).read().decode()
    d = pd.read_csv(io.StringIO(raw)); d.columns = ['d', 's']
    d['d'] = pd.to_datetime(d['d']); d['s'] = pd.to_numeric(d['s'], errors='coerce')
    return d.dropna()


def _local(path):
    p = os.path.join(WORK, path)
    if not os.path.exists(p):
        return None
    d = pd.read_csv(p)
    if 'DATE' in d.columns:
        d = d.rename(columns={'DATE': 'd', 'CLOSE': 's'})[['d', 's']]
    elif 'observation_date' in d.columns:
        d = d.rename(columns={'observation_date': 'd', 'SP500': 's'})[['d', 's']]
    else:
        d = d.rename(columns={d.columns[0]: 'd', d.columns[1]: 's'})[['d', 's']]
    d['d'] = pd.to_datetime(d['d']); d['s'] = pd.to_numeric(d['s'], errors='coerce')
    return d.dropna()


def load_asset(key):
    """源链: 远端刷新(合并去重) → 本地兜底。返回(df, source, stale_days)"""
    a = ASSETS[key]
    base = _local(a['local'])
    fresh = None
    if a['yahoo']:
        fresh = _yahoo(a['yahoo'])
    if fresh is None and a['fred']:
        try:
            fresh = _fred(a['fred'])
        except Exception:
            fresh = None
    src = 'local'
    if fresh is not None and len(fresh):
        if base is None:
            base, src = fresh, a['yahoo'] or 'fred'
        else:
            n0 = len(base)
            base = pd.concat([base, fresh]).drop_duplicates('d').sort_values('d')
            src = (a['yahoo'] or 'fred') if len(base) > n0 else 'local(无新数据)'
    if base is None:
        return None, 'absent', 9999
    # 写回本地(CI提交即持久化)
    out = os.path.join(WORK, a['local'])
    base.to_csv(out, index=False)
    stale = (pd.Timestamp.utcnow().tz_localize(None) - base['d'].iloc[-1]).days
    return base, src, stale


def indicators(d):
    s = d['s']
    ret = s.pct_change()
    rv20 = float(ret.rolling(20).std().iloc[-1] * np.sqrt(252) * 100) if len(ret) > 21 else None
    rv_hist = ret.rolling(20).std().dropna() * np.sqrt(252) * 100
    window = rv_hist.iloc[-756:] if len(rv_hist) > 756 else rv_hist
    rv_pct = float((window <= rv_hist.iloc[-1]).mean() * 100) if len(rv_hist) > 60 else None
    mom = lambda n: float((s.iloc[-1] / s.iloc[-1 - n] - 1) * 100) if len(s) > n else None
    return dict(last=float(s.iloc[-1]), date=str(d['d'].iloc[-1].date()),
                chg1d=mom(1), mom20=mom(20), mom60=mom(60), rv20=rv20, rv_pct3y=rv_pct)


def build_pulse():
    snap, srcs = {}, {}
    for k in ASSETS:
        d, src, stale = load_asset(k)
        if d is None:
            snap[k] = dict(name=ASSETS[k]['name'], market=ASSETS[k]['market'], status='absent')
            continue
        ind = indicators(d)
        ind.update(name=ASSETS[k]['name'], market=ASSETS[k]['market'], source=src, stale_days=stale)
        snap[k] = ind; srcs[k] = src

    sigs = []
    def add(sid, level, text):
        sigs.append(dict(id=sid, level=level, text=text))

    vix_pct = snap.get('VIX', {}).get('rv_pct3y')  # VIX用自身3年分位
    v = snap.get('VIX', {})
    if v.get('last'):
        vpct = None
    # VIX信号: 用点位+3年分位(点位即波动率)
    for mkey, label in [('CN300', 'CN'), ('HK', 'HK'), ('SPX', 'US')]:
        a = snap.get(mkey, {})
        pct = a.get('rv_pct3y')
        if pct is None:
            continue
        if pct <= 33:
            add(f'TICKET-ENTRY-{label}', 'opportunity',
                f'{a["name"]} 波动率3年分位{pct:.0f}% ≤33% — T33/T34票据入场窗(回卷基点)')
        elif pct >= 90:
            add(f'DANGER-{label}', 'critical',
                f'{a["name"]} 波动率3年分位{pct:.0f}% ≥90% — 收缩类外区, 剪枝策略禁用, 票据兑付期')
    if v.get('last') is not None:
        if v['last'] <= 14:
            add('TICKET-ENTRY-US-VIX', 'opportunity', f'VIX={v["last"]:.1f}≤14 — 美股票据便宜区(S2)')
        elif v['last'] >= 30:
            add('DANGER-US-VIX', 'critical', f'VIX={v["last"]:.1f}≥30 — 类外区, 禁用一切卖方结构')
    # 跨市场联动
    cn, us, hk = snap.get('CN300', {}), snap.get('SPX', {}), snap.get('HK', {})
    if cn.get('mom20') is not None and us.get('mom20') is not None:
        dv = cn['mom20'] - us['mom20']
        if abs(dv) >= 8:
            add('DIVERGENCE-CN-US', 'warning',
                f'中美20日动量背离 {dv:+.1f}pt (CN {cn["mom20"]:+.1f}% vs US {us["mom20"]:+.1f}%) — 叙事浓度差, 检查汇率/政策叙事')
    if hk.get('mom20') is not None and cn.get('mom20') is not None:
        dv = hk['mom20'] - cn['mom20']
        if abs(dv) >= 6:
            add('DIVERGENCE-HK-CN', 'warning',
                f'A/H(代理)20日动量差 {dv:+.1f}pt — 港股定价权在外资, 背离常先收于港股侧')

    opinions = {}
    for k in ('CN300', 'HK', 'SPX'):
        a = snap.get(k, {})
        if not a.get('last'):
            continue
        pct = a.get('rv_pct3y')
        if pct is None:
            opinions[k] = '数据不足, 观望'
        elif pct <= 33:
            opinions[k] = f'票据窗开(分位{pct:.0f}%): 按T33/T34以低波基点建票据腿, 禁裸卖'
        elif pct >= 90:
            opinions[k] = f'类外区(分位{pct:.0f}%): 只持有票据+安全基点, 收割面全面停'
        else:
            opinions[k] = f'中性区(分位{pct:.0f}%): 长端收割+票据组合体可运行, 仓位随分位递增递减'

    pulse = dict(updated=time.strftime('%Y-%m-%d %H:%M:%S'), assets=snap, signals=sigs,
                 opinions=opinions, sources=srcs,
                 theorems=['T32', 'T33', 'T34', 'E5'])
    json.dump(pulse, open(os.path.join(WORK, 'market_pulse.json'), 'w'), ensure_ascii=False, indent=1)
    return pulse


if __name__ == '__main__':
    p = build_pulse()
    for k, a in p['assets'].items():
        if a.get('last'):
            print(f"{k:6s} {a['name']:12s} {a['last']:>10.2f} 1d={a.get('chg1d') or 0:+.2f}% "
                  f"rv20={a.get('rv20') or 0:.1f}% 分位={a.get('rv_pct3y') or 0:.0f}% [{a['source']}] stale={a['stale_days']}d")
    for s in p['signals']:
        print(f"[{s['level']:11s}] {s['text']}")
