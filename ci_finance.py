# -*- coding: utf-8 -*-
"""v∞ CI金融日更 (第47章) — 实时金融数据/工具/资源
FRED免key源(SP500/VIXCLS) → 更新本地CSV → 重算T33策略台账指标 → strategies.json → bundle。
"""
import os, sys, json, time, urllib.request, io
import numpy as np
import pandas as pd

WORK = os.path.dirname(os.path.abspath(__file__))
os.environ['VINF_WORK'] = WORK
os.chdir(WORK)

FRED = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id={}'
YAHOO = 'https://query1.finance.yahoo.com/v8/finance/chart/{}?period1=1451606400&period2={}&interval=1d'
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36'}
TICKER = {'SP500': '%5EGSPC', 'VIXCLS': '%5EVIX'}


def _parse(d):
    d.columns = ['d', 'v']
    d['d'] = pd.to_datetime(d['d'])
    d['v'] = pd.to_numeric(d['v'], errors='coerce')
    return d.dropna()


def _fred(series):
    raw = urllib.request.urlopen(urllib.request.Request(FRED.format(series), headers=UA), timeout=90).read().decode()
    return _parse(pd.read_csv(io.StringIO(raw)))


def _yahoo(series):
    import json as _json
    raw = urllib.request.urlopen(urllib.request.Request(
        YAHOO.format(TICKER[series], int(time.time())), headers=UA), timeout=90).read().decode()
    r = _json.loads(raw)['chart']['result'][0]
    ts = r['timestamp']; cl = r['indicators']['quote'][0]['close']
    return _parse(pd.DataFrame({'d': pd.to_datetime(ts, unit='s').date, 'v': cl}))


STOOQ = {'SP500': '^spx', 'VIXCLS': '^vix', 'DGS10': '10yusy', 'DEXCHUS': 'usdcny'}


def _stooq(series):
    raw = urllib.request.urlopen(urllib.request.Request(
        f'https://stooq.com/q/d/l/?s={STOOQ[series]}&i=d', headers=UA), timeout=60).read().decode()
    if 'Date,' not in raw[:50]:
        raise RuntimeError('stooq challenge/empty')
    return _parse(pd.read_csv(io.StringIO(raw)).rename(columns={'Date': 'd', 'Close': 'v'})[['d', 'v']])


def fetch(series):
    """多源容灾: FRED → Yahoo → Stooq; 皆败则回退本地CSV(数据不更新但回测照跑)"""
    for src in (_fred, _yahoo, _stooq):
        for attempt in range(2):
            try:
                return src(series)
            except Exception as e:
                print(f"  fetch {series} via {src.__name__}#{attempt+1}: {type(e).__name__}")
                time.sleep(10 * (attempt + 1))
    print(f"  FALLBACK: 使用本地既有{series}数据")
    if series == 'SP500' and os.path.exists('spx_fred.csv'):
        d = pd.read_csv('spx_fred.csv'); d.columns = ['d', 'v']
        return _parse(d)
    if os.path.exists('vix_hist.csv'):
        d = pd.read_csv('vix_hist.csv')[['DATE', 'CLOSE']]; d.columns = ['d', 'v']
        return _parse(d)
    raise RuntimeError(f'{series}: 所有源失败且无本地备份')


def main():
    spx = fetch('SP500'); vix = fetch('VIXCLS')
    # 更新本地CSV(保持既有格式)
    spx.rename(columns={'v': 'SP500'}).assign(observation_date=spx['d'].dt.strftime('%Y-%m-%d'))[
        ['observation_date', 'SP500']].to_csv('spx_fred.csv', index=False)
    vix.assign(DATE=vix['d'].dt.strftime('%m/%d/%Y'), OPEN=vix['v'], HIGH=vix['v'],
               LOW=vix['v'], CLOSE=vix['v'])[['DATE', 'OPEN', 'HIGH', 'LOW', 'CLOSE']].to_csv('vix_hist.csv', index=False)
    print(f"data: SPX→{spx['d'].iloc[-1].date()} {spx['v'].iloc[-1]:.0f}, VIX→{vix['d'].iloc[-1].date()} {vix['v'].iloc[-1]:.2f}")

    # T33回测(首破准则, 与第45章同一代码路径)
    df = spx.rename(columns={'v': 's'}).merge(vix, on='d').sort_values('d').reset_index(drop=True)
    df['ym'] = df['d'].dt.to_period('M')
    df['ret0'] = df.groupby('ym')['s'].transform(lambda s: s / s.iloc[0] - 1)
    br = df.groupby('ym').agg(breach=('ret0', lambda x: x.abs().max()), v0=('v', 'first')).dropna()
    br['sig'] = br['v0'] / 100 * np.sqrt(1 / 12)
    br['payoff'] = (br['breach'] - 0.5 * br['sig']).clip(lower=0)
    br['prem'] = 0.40 * br['sig']
    br['short'] = br['prem'] - br['payoff']; br['long'] = -br['short']
    br['base'] = (br['v0'].rolling(36, min_periods=12)
                  .apply(lambda x: (x[-1] <= np.quantile(x, 1 / 3)) * 1.0, raw=True)) == 1.0
    rng = np.random.default_rng(7)
    br['rand'] = rng.random(len(br)) < 0.33

    def stat(pnl):
        p = pnl.fillna(0) / br['sig'].mean()
        cum = p.cumsum()
        return dict(cum_pnl=round(float(cum.iloc[-1]), 1),
                    max_dd=round(float(-(cum - cum.cummax()).min()), 1),
                    worst_month=round(float(p.min()), 2), best_month=round(float(p.max()), 2))

    res = {'S1-SHORTWING': stat(br['short']), 'S2-CORE': stat(br['long'].where(br['base'])),
           'S0-REINIT': stat(br['long'].where(br['rand']))}
    for k, v in res.items():
        print(f"  {k}: {v}")

    # 更新策略台账
    book = json.load(open('strategies.json'))
    for s in book['strategies']:
        if s['id'] in res:
            s['metrics'].update(res[s['id']])
    book['meta']['updated'] = time.strftime('%Y-%m-%d')
    book['meta']['data'] = f"SPX(FRED)+VIX, {df['d'].iloc[0].date()} ~ {df['d'].iloc[-1].date()}, 月度调仓(CI日更)"
    json.dump(book, open('strategies.json', 'w'), ensure_ascii=False, indent=2)

    # 续链一跳
    lines = open('journal39.jsonl').read().strip().split('\n')
    prev = json.loads(lines[-1])['hash']
    import hashlib
    actions = [f"finance-daily: SPX→{spx['d'].iloc[-1].date()}, VIX→{vix['d'].iloc[-1].date()}",
               f"backtest: S2={res['S2-CORE']['cum_pnl']}σ/DD{res['S2-CORE']['max_dd']}, "
               f"S1={res['S1-SHORTWING']['cum_pnl']}σ(禁用项留档)",
               f"strategies.json updated {book['meta']['updated']}"]
    rec = dict(tick=int(time.time()), ts=time.strftime('%Y-%m-%d %H:%M:%S'), actions=actions, prev_hash=prev)
    rec['hash'] = hashlib.sha256((prev + json.dumps(actions, ensure_ascii=False)).encode()).hexdigest()
    open('journal39.jsonl', 'a').write(json.dumps(rec, ensure_ascii=False) + '\n')
    print(f"journal: {len(lines)+1} hops, tail={rec['hash'][:12]}")
    print('CI_FINANCE_OK')


if __name__ == '__main__':
    main()
