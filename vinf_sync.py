# -*- coding: utf-8 -*-
"""v∞ 外部状态总线（第40章）——GitHub作为跨沙箱单一事实源
心跳任何沙箱再入时: 先 restore(clone/pull) → tick → backup(push)。
教训(手机端首跳): 心跳沙箱与本体会话的/mnt不互通, 无Git状态总线则Kernel 0式种子重建。
"""
import os, subprocess, sys, shutil

REPO_URL = 'https://{token}@github.com/chepin-ai/vinf-market-kernel.git'
REPO_DIR = '/tmp/vinf_repo'
WORK = '/mnt/agents/work/worldcup2026'

# 纳入版本管理的状态文件（密钥与大数据永不出境）
TRACKED = [
    'vinf_agents.py', 'vinf_provers.py', 'vinf_resolver.py', 'vinf_os.py',
    'vinf_finance.py', 'vinf_console.py', 'vinf_policy.json', 'v39_demo.py',
    'vinf_maxitive.py', 'vinf_data.py', 'vinf_engine.py', 'backtest_real_2014_2026.py',
    'bl_reconstruction.py', 'MarketKernel.lean',
    'theory_db.sqlite', 'journal39.jsonl', 'pool.json',
    'vrp_ladder.csv', 'dalpha_ladder.csv', 'dalpha_trimmed.csv',
    'heartbeat_status.json', 'kg.json', 'STATUS.md', 'state_bundle.json',
    'vinf_kg.py', 'vinf_sync.py',
]

def _git(*args, cwd=REPO_DIR, check=True):
    r = subprocess.run(['git', *args], cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f'git {args[0]}: {r.stderr[:200]}')
    return r.stdout.strip()

def token():
    tf = os.path.join(WORK, 'vinf_keys.json')
    if os.path.exists(tf):
        import json
        return json.load(open(tf)).get('github', '')
    return os.environ.get('VINF_GH_TOKEN', '')

def restore():
    """克隆或拉取最新状态; 返回状态目录路径"""
    if os.path.isdir(os.path.join(REPO_DIR, '.git')):
        _git('fetch', 'origin'); _git('reset', '--hard', 'origin/main')
    else:
        if os.path.exists(REPO_DIR):
            shutil.rmtree(REPO_DIR)
        subprocess.run(['git', 'clone', REPO_URL.format(token=token()), REPO_DIR],
                       capture_output=True, check=True)
    return REPO_DIR

def backup(msg='heartbeat tick'):
    """把工作区TRACKED文件提交并推送（无本地仓库时自愈初始化）"""
    if not os.path.isdir(os.path.join(REPO_DIR, '.git')):
        init_repo()
    os.makedirs(REPO_DIR, exist_ok=True)
    for f in TRACKED:
        src = os.path.join(WORK, f)
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(REPO_DIR, f))
    _git('add', '-A')
    if not _git('status', '--porcelain'):
        return 'no-change'
    _git('commit', '-m', f'[v∞] {msg}')
    _git('push', 'origin', 'HEAD:main')
    return _git('rev-parse', '--short', 'HEAD')

def init_repo():
    """首次装配: 配置身份/远端/.gitignore"""
    os.makedirs(REPO_DIR, exist_ok=True)
    if not os.path.isdir(os.path.join(REPO_DIR, '.git')):
        subprocess.run(['git', 'init', '-b', 'main'], cwd=REPO_DIR, capture_output=True)
    _git('config', 'user.email', 'vinf@kernel.dev')
    _git('config', 'user.name', 'v-infinity kernel')
    _git('remote', 'remove', 'origin', check=False)
    _git('remote', 'add', 'origin', REPO_URL.format(token=token()))
    with open(os.path.join(REPO_DIR, '.gitignore'), 'w') as f:
        f.write('vinf_keys.json\nspypart_*\n*.zip\n__pycache__/\n*.png\n'
                'cs2_*.csv\nnewest_ts_ds.csv\nucl_30k_matches.csv\n'
                'worldcup_2026_odds_snapshot.csv\nwc2026*.xlsx\ngspc*.csv\n'
                'spx_*.csv\nvix*.csv\nspy_*.csv\nhistorical_matches*.csv\nepl_*.csv\n')

if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'backup'
    if cmd == 'init':
        init_repo(); print(backup('initial state'))
    elif cmd == 'restore':
        print('restored →', restore())
    elif cmd == 'backup':
        print(backup(' '.join(sys.argv[2:]) or 'manual backup'))
