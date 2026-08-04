#!/usr/bin/env python3
"""v∞ 命令注册表 — 响应指令单的可执行闭环
Dashboard每条告警的响应指令单携带命令令牌(RUN <CMD>), 粘贴回v∞会话即由本注册表
确定性执行; 执行结果写入journal留链, 疗效由下一心跳自动验证(告警消除=验证通过)。
浏览器无写凭据: 会话(人+助手)是执行面, 注册表是唯一的命令语义源(代码才判决)。
"""
import json
import os
import subprocess
import sys
import time

WORK = os.path.dirname(os.path.abspath(__file__))


def _run(script, *args, timeout=600):
    r = subprocess.run([sys.executable, os.path.join(WORK, script), *args],
                       capture_output=True, text=True, timeout=timeout, cwd=WORK)
    return dict(rc=r.returncode, out=(r.stdout + r.stderr)[-400:])


def cmd_REFRESH_CN(_):
    """iFinD刷新CN系+板块全池(增量10日)"""
    return _run('vinf_refresh_cn.py')


def cmd_REFRESH_CN_FULL(_):
    """iFinD全量回补(1090天分块, 多日下载策略)"""
    return _run('vinf_refresh_cn.py', '--full')


def cmd_FIN_STATUS(_):
    """重跑金融四检并刷新heartbeat_status(修复状态滞后)"""
    return _run('vinf_console.py', 'status')


def cmd_DOCTOR(_):
    """内核自检/自验证/自修复全流程"""
    return _run('vinf_doctor.py')


def cmd_BUNDLE(_):
    """重建状态包"""
    return _run('vinf_console.py', 'bundle')


def cmd_ONTOLOGY(_):
    """本体导出+推理机(自推演/自验证/自涌现)"""
    a = _run('vinf_ontology.py')
    b = _run('vinf_reasoner.py')
    return dict(rc=max(a['rc'], b['rc']), out=a['out'] + ' | ' + b['out'])


COMMANDS = {k[4:].replace('_', '-'): v for k, v in list(globals().items()) if k.startswith('cmd_')}


def execute(cmd, arg=None):
    if cmd not in COMMANDS:
        return dict(rc=127, out=f'未知命令: {cmd} · 可用: {list(COMMANDS)}')
    res = COMMANDS[cmd](arg)
    res['cmd'] = cmd
    res['ts'] = time.strftime('%Y-%m-%d %H:%M:%S')
    # 留痕(本地执行日志, 不入链——入链由心跳/journal负责)
    log = os.path.join(WORK, 'command_log.jsonl')
    open(log, 'a').write(json.dumps(res, ensure_ascii=False) + '\n')
    return res


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'DOCTOR'
    print(json.dumps(execute(cmd), ensure_ascii=False, indent=1))
