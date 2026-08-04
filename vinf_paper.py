# -*- coding: utf-8 -*-
"""v∞ 虚拟盘引擎 (第49章) — A股long-only轮动策略的前瞻纸面验证
规则(与回测同构, 冻结于建盘日): 月度调仓(每21交易日); 板块63日动量前2等权;
CN300 RV20三年分位>90% → 全部切换红利(类外避险); 单边成本0.1%。
台账: virtual_portfolio.json — 只增不减, 每次脉搏运行时盯市+检查调仓。"""
import os, json, time
import numpy as np
import pandas as pd

WORK = os.path.dirname(os.path.abspath(__file__))
SECTORS = ['证券', '银行', '酒', '医疗', '半导体', '有色']
COST = 0.001
LEDGER = os.path.join(WORK, 'virtual_portfolio.json')


def _load():
    px = pd.read_csv(os.path.join(WORK, 'sector_etf.csv'), parse_dates=['d'])
    px = px.pivot_table(index='d', columns='name', values='s').sort_index().dropna()
    cn = pd.read_csv(os.path.join(WORK, 'csi300.csv'), parse_dates=['d']).set_index('d')['s']
    return px, cn


def _regime(cn, d):
    rv = cn.pct_change().rolling(20).std() * np.sqrt(252) * 100
    w = rv.loc[:d].iloc[-756:]
    return float((w <= w.iloc[-1]).mean() * 100)


def signal(px, cn, d):
    mom63 = px.pct_change(63).loc[d].dropna().sort_values(ascending=False)
    pct = _regime(cn, d)
    target = ['红利'] if pct > 90 else list(mom63.index[:2])
    return target, pct, mom63


def step():
    """盯市 + 规则化调仓检查; 返回(ledger, 本日动作)"""
    px, cn = _load()
    d = px.index[-1]
    if os.path.exists(LEDGER):
        led = json.load(open(LEDGER))
    else:
        led = dict(strategy='M5-A股行业轮动(long-only)', rules='63日动量前2等权/月度调仓/类外(>90%)切换红利/单边0.1%',
                   inception=str(d.date()), nav=1.0, positions=[], nav_history=[], trades=[])
    # 盯市: 自上次记录以来的等权组合收益
    if led['positions']:
        last_d = pd.Timestamp(led['nav_history'][-1]['date']) if led['nav_history'] else None
        if last_d is not None and last_d < d:
            r = float(np.mean([px[c].loc[d] / px[c].loc[last_d] - 1
                               for c in led['positions'] if c in px.columns]))
            led['nav'] *= (1 + r)
    led['nav_history'].append(dict(date=str(d.date()), nav=round(led['nav'], 6)))

    # 调仓检查: 新数据日且(建盘/距上次调仓≥21交易日/制度翻转)
    action = 'hold'
    last_reb = pd.Timestamp(led['trades'][-1]['date']) if led['trades'] else None
    idx = list(px.index).index(d)
    due = (last_reb is None) or (idx - list(px.index).index(last_reb) >= 21 if last_reb in px.index else True)
    if due:
        target, pct, mom63 = signal(px, cn, d)
        if set(target) != set(led['positions']):
            if led['positions']:
                led['nav'] *= (1 - COST) ** len(set(target) ^ set(led['positions']))
            why = '类外避险' if pct > 90 else ('建盘' if last_reb is None else '轮动')
            led['trades'].append(dict(date=str(d.date()), sell=led['positions'], buy=target,
                                      why=why, rv_pct=round(pct, 1), nav=round(led['nav'], 6)))
            led['positions'] = target
            action = f"rebalance→{target}({why}, 分位{pct:.0f}%)"
    json.dump(led, open(LEDGER, 'w'), ensure_ascii=False, indent=1)
    return led, action


def board(led, px, cn):
    """给market_pulse用的轮动板块视图"""
    d = px.index[-1]
    mom63 = px.pct_change(63).loc[d]
    mom20 = px.pct_change(20).loc[d]
    rows = []
    for c in SECTORS + ['红利', '沪深300ETF', '黄金现货']:
        if c in px.columns:
            rows.append(dict(asset=c, mom20=round(float(mom20.get(c, np.nan)) * 100, 1),
                             mom63=round(float(mom63.get(c, np.nan)) * 100, 1),
                             held=c in led['positions']))
    rows.sort(key=lambda r: -(r['mom63'] if r['mom63'] == r['mom63'] else -999))
    bm = px['沪深300ETF'] / px['沪深300ETF'].iloc[0]
    out = dict(date=str(d.date()), rows=rows, positions=led['positions'], nav=led['nav'],
               inception=led['inception'], n_trades=len(led['trades']),
               bm_since_inception=round(float(bm.iloc[-1] / bm.loc[pd.Timestamp(led['inception'])] - 1) * 100, 2)
               if pd.Timestamp(led['inception']) in bm.index else None,
               trades=led['trades'][::-1],
               nav_history=led.get('nav_history', []))
    # 回测全史(前瞻判决器的参照系): 轮动NAV vs 沪深300ETF, 降采样至~120点
    try:
        bt = pd.read_csv(os.path.join(os.path.dirname(__file__), 'rotation_nav.csv'),
                         index_col=0, parse_dates=True)['nav']
        step_n = max(1, len(bt) // 120)
        bt_d = bt.iloc[::step_n]
        bm3 = px['沪深300ETF'].reindex(bt.index).ffill()
        bm3 = (bm3 / bm3.iloc[0]).iloc[::step_n]
        out['backtest'] = [dict(date=str(i.date()), nav=round(float(v), 3),
                                bm=round(float(bm3.loc[i]), 3)) for i, v in bt_d.items()]
    except Exception:
        out['backtest'] = []
    # 当前态势判定: 用代码把"为什么持有这些仓位"讲清楚
    try:
        rv = cn.pct_change().rolling(20).std() * np.sqrt(252) * 100
        hist = rv.iloc[-756:] if len(rv) > 756 else rv
        pct = float((hist <= rv.iloc[-1]).mean() * 100)
        if pct >= 90:
            stance = f'类外区(波动分位{pct:.0f}%≥90%): T33/T34判决——卖方剪枝禁用, 轮动自动切红利避险; 当前持仓即判决的执行'
        elif pct <= 33:
            stance = f'票据窗口(波动分位{pct:.0f}%≤33%): 低波基点附近, 允许动量持仓, 关注TICKET-ENTRY'
        else:
            stance = f'常态区(波动分位{pct:.0f}%): 按63日动量前2等权持仓, 月度调仓'
        out['stance'] = dict(rv_pct=round(pct, 1), text=stance)
    except Exception:
        pass
    return out


if __name__ == '__main__':
    px, cn = _load()
    led, act = step()
    b = board(led, px, cn)
    print('虚拟盘 NAV:', round(led['nav'], 4), '持仓:', led['positions'], '动作:', act)
    for r in b['rows'][:4]:
        print(f"  {r['asset']:6s} 20日{r['mom20']:+}% 63日{r['mom63']:+}% {'[持有]' if r['held'] else ''}")
