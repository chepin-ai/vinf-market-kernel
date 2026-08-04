# -*- coding: utf-8 -*-
"""v∞ CI看门狗 (第47章) — 每周巡检: 链完整性 + 心跳活性 + 台账一致性
断链或心跳失联(>4天) → 退出码1 → Actions红徽章(全局可见的报警)。"""
import os, sys, json, time

WORK = os.path.dirname(os.path.abspath(__file__))
os.environ['VINF_WORK'] = WORK
os.chdir(WORK)
sys.path.insert(0, WORK)
import vinf_console as vc


def main():
    v = vc.verify_chain()
    st = vc.status(write=False)
    last = json.loads(open('journal39.jsonl').read().strip().split('\n')[-1])
    age_h = (time.time() - last['tick']) / 3600
    stale = age_h > 96
    lines = [
        f"# v∞ 看门狗周报 ({time.strftime('%Y-%m-%d %H:%M')} UTC)",
        '',
        f"- 哈希链: {'✅' if v['ok'] else '❌ ' + v['detail']} ({v.get('hops')}跳, 尾 {v.get('tail')})",
        f"- 末跳年龄: {age_h:.1f}h {'✅' if not stale else '❌ 失联>96h'}",
        f"- 定理: {st['db']['theorems']} | 前沿: {st['db']['frontier']} | 数据债: {st['db']['debts']}",
        f"- 金融: " + ' ; '.join(st.get('finance', [])),
        f"- 时间线: 本体沙箱 / 手机心跳 / GitHub Actions 三线并轨, 单一事实源=本仓库",
    ]
    open('WATCHDOG.md', 'w').write('\n'.join(lines) + '\n')
    print('\n'.join(lines))
    if not v['ok'] or stale:
        print('WATCHDOG_ALARM'); sys.exit(1)
    print('WATCHDOG_OK')


if __name__ == '__main__':
    main()
