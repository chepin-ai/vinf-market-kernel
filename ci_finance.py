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


def fetch(series):
    last = None
    for attempt in range(4):
        try:
            req = urllib.request.Request(FRED.format(series), headers={'User-Agent': 'Mozilla/5.0'})
            raw = urllib.request.urlopen(req, timeout=90).read().decode()
            break
        except Exception as e:
            last = e; time.sleep(15 * (attempt + 1))
    else:
        raise last
    d = pd.read_csv(io.StringIO(raw))
    d.columns = ['d', 'v']
    d['d'] = pd.to_datetime(d['d'])
    d['v'] = pd.to_numeric(d['v'], errors='coerce')
    return d.dropna()


def main():
    spx = fetch('SP500'); vix = fetch('VIXCLS')
    # 更新本地CSV(保持既有格式)
    spx.rename(columns={'v': 'SP500'}).assign(observation_date=spx['d'].dt.strftime('%Y-%m-%d'))[
        ['observation_date', 'SP500']].to_csv('spx_fred.csv', index=False)
    vix.assign(DATE=vix['d'].dt.strftime('%m/%d/%Y'), OPEN=vix['v'], HIGH=vix['v'],
               LOW=vix['v'], CLOSE=vix['v'])[['DATE', 'OPEN', 'HIGH', 'LOW', 'CLOSE']].to_csv('vix_hist.csv', index=False)
    print(f"data: SPX→{spx['d'].iloc[-1].date()} {spx['v'].iloc[-1]:.0f}, VIX→{vix['d'].iloc[-1].date()} {vix['v'].iloc[-1]:.2f}")

    # T33回测(首破准则, 与第45章同一代码路径)
    df = spx.merge(vix, on='d').sort_values('d').reset_index(drop=True)
    df['ym'] = df['d'].dt.to_period('M')
    df['ret0'] = df.groupby('ym')['v_x' if 'v_x' in df else 'v'].transform(lambda s: s / s.iloc[0] - 1)
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
