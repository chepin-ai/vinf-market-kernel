#!/usr/bin/env python3
"""v∞ CN系数据刷新器 — iFinD通道(沙箱/CI双可达) · 多源容灾 · 多日分块策略
限制与对策:
- iFinD 单次≤3 ticker、跨度≤1095天 → 分块循环(多日下载策略)
- 每日限额 → 增量刷新(默认仅取近10天, 成本恒定)
- 全失败 → 保留本地CSV, 如实报告(永不伪造)
用法: python3 vinf_refresh_cn.py [--days N] [--full]
"""
import io
import json
import os
import subprocess
import sys
import time

import pandas as pd

WORK = os.path.dirname(os.path.abspath(__file__))
IFIND = '/app/.agents/plugins/ifind/scripts/ifind_tool.py'

# (代码, 本地CSV, 长表名或None)
TARGETS = [
    ('000300.SH', 'csi300.csv', None),
    ('000001.SH', 'shcomp.csv', None),
    ('0700.HK', 'tencent_hk.csv', None),
    ('AU9999.SHG', 'gold.csv', None),
    ('512880.SH', 'sector_etf.csv', '证券'),
    ('512170.SH', 'sector_etf.csv', '医疗'),
    ('512400.SH', 'sector_etf.csv', '有色'),
    ('512480.SH', 'sector_etf.csv', '半导体'),
    ('510880.SH', 'sector_etf.csv', '红利'),
    ('512800.SH', 'sector_etf.csv', '银行'),
    ('512690.SH', 'sector_etf.csv', '酒'),
    ('510300.SH', 'sector_etf.csv', '沪深300ETF'),
]
# 黄金现货同时入 sector_etf 长表
EXTRA_LONG = {'AU9999.SHG': '黄金现货'}


def ifind_fetch(codes, start, end, out):
    """一次≤3个ticker"""
    if not os.path.exists(IFIND):
        return None
    r = subprocess.run([sys.executable, IFIND, 'call', '--api-name', 'ifind_get_price',
                        '--params-json', json.dumps(dict(
                            ticker=','.join(codes), start_date=start, end_date=end,
                            file_path=out))],
                       capture_output=True, text=True, timeout=180, cwd=os.path.dirname(IFIND))
    if not os.path.exists(out):
        return None
    d = pd.read_csv(out)
    if d.empty or 'close' not in d.columns:
        return None
    return d[['thscode', 'time', 'close']].rename(
        columns={'thscode': 'code', 'time': 'd', 'close': 's'})


def merge(path, code, add, name=None):
    old = pd.read_csv(path, dtype=str) if os.path.exists(path) else pd.DataFrame()
    a = add[add.code == code].copy()
    if a.empty:
        return 0
    a['d'] = pd.to_datetime(a['d']).dt.strftime('%Y-%m-%d')
    if 'code' in old.columns or name is not None:
        a = a.assign(name=name)[['d', 's', 'code', 'name']]
        old = old[~old.set_index(['d', 'code']).index.isin(a.set_index(['d', 'code']).index)] if len(old) else old
        out = pd.concat([old, a]).sort_values(['d', 'code'])
    else:
        a = a[['d', 's']]
        old = old[~old['d'].isin(a['d'])] if len(old) else old
        out = pd.concat([old, a]).sort_values('d')
    out.to_csv(path, index=False)
    return len(a)


def refresh(days=10, full=False):
    end = time.strftime('%Y-%m-%d')
    start = (pd.Timestamp(end) - pd.Timedelta(days=1090 if full else days + 4)).strftime('%Y-%m-%d')
    codes = sorted({t[0] for t in TARGETS})
    got = {}
    for i in range(0, len(codes), 3):  # 分块: ≤3/次
        chunk = codes[i:i + 3]
        out = f'/tmp/ifind_{i}.csv'
        d = ifind_fetch(chunk, start, end, out)
        if d is not None:
            for _, r in d.iterrows():
                got.setdefault(r['code'], []).append((r['d'], r['s']))
        time.sleep(1)  # 限额礼仪
    allrows = pd.DataFrame([(c, d, s) for c, rows in got.items() for d, s in rows],
                           columns=['code', 'd', 's'])
    report = {}
    for code, path, name in TARGETS:
        n = merge(os.path.join(WORK, path), code, allrows, name) if len(allrows) else 0
        report[code] = n
    # 黄金入长表
    if len(allrows):
        merge(os.path.join(WORK, 'sector_etf.csv'), 'AU9999.SHG', allrows, EXTRA_LONG['AU9999.SHG'])
    return report


if __name__ == '__main__':
    days = 10
    full = '--full' in sys.argv
    if '--days' in sys.argv:
        days = int(sys.argv[sys.argv.index('--days') + 1])
    rep = refresh(days=days, full=full)
    ok = sum(1 for v in rep.values() if v)
    print(f'iFinD刷新: {ok}/{len(rep)}代码有数 · {json.dumps(rep)}')
    sys.exit(0 if ok else 1)
