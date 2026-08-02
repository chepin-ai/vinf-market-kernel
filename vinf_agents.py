# vinf_agents.py — v∞ 多LLM协同层 (第37章)
# 设计公理(框架自治): A2'/T9 — LLM只提案, 代码才判决 (任何LLM断言须经可执行核验)
#                     T26 — 共识=均值池(证据), 否决=最大池(异议取sup)
# 组件: LLMClient(三通道) / TheoryDB(理论记忆库) / Panel(立论-证伪-核验-登记回路)
import sqlite3, json, os, time, urllib.request

KEYS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'vinf_keys.json')
LLMS = {
    'deepseek': dict(url='https://api.deepseek.com/v1/chat/completions', model='deepseek-v4-pro'),
    'deepseek-flash': dict(url='https://api.deepseek.com/v1/chat/completions', model='deepseek-v4-flash'),
    'longcat': dict(url='https://api.longcat.chat/openai/v1/chat/completions', model='LongCat-2.0'),
    'kimi': dict(url='https://api.moonshot.cn/v1/chat/completions', model='kimi-k2.6'),
}

def _key(name):
    if os.path.exists(KEYS_FILE):
        return json.load(open(KEYS_FILE)).get(name.split('-')[0])
    return os.environ.get(f'VINF_KEY_{name.upper()}')

def chat(llm, prompt, system=None, max_tokens=1600, temperature=None, timeout=180):
    """统一OpenAI兼容调用; 推理模型自动回退reasoning_content; 返回文本或错误串"""
    cfg = LLMS[llm]; key = _key(llm)
    msgs = ([{'role':'system','content':system}] if system else []) + [{'role':'user','content':prompt}]
    payload = {'model':cfg['model'],'messages':msgs,'max_tokens':max_tokens}
    if temperature is not None: payload['temperature'] = temperature
    body = json.dumps(payload).encode()
    req = urllib.request.Request(cfg['url'], data=body, method='POST',
        headers={'Authorization':f'Bearer {key}','Content-Type':'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            d = json.loads(r.read())
        m = d['choices'][0]['message']
        out = m.get('content') or m.get('reasoning_content') or '(空响应)'
        return out
    except Exception as e:
        return f'(调用失败: {e})'

class TheoryDB:
    """理论记忆数据库: 定理/预测/数据资产/数据债/前沿发现 五表"""
    def __init__(self, path='theory_db.sqlite'):
        self.db = sqlite3.connect(path); self._init()
    def _init(self):
        c = self.db.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS theorems(
            id TEXT PRIMARY KEY, kind TEXT, statement TEXT, status TEXT,
            deps TEXT, evidence TEXT, verified_by TEXT, round INTEGER, updated TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS predictions(
            id TEXT PRIMARY KEY, statement TEXT, test_by TEXT, status TEXT, note TEXT, updated TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS assets(
            name TEXT PRIMARY KEY, kind TEXT, source TEXT, note TEXT, updated TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS debts(
            id INTEGER PRIMARY KEY AUTOINCREMENT, item TEXT, status TEXT, note TEXT, updated TEXT)''')
        c.execute('''CREATE TABLE IF NOT EXISTS frontier(
            id INTEGER PRIMARY KEY AUTOINCREMENT, finding TEXT, source TEXT, impact TEXT, round INTEGER, updated TEXT)''')
        self.db.commit()
    def put(self, table, **kw):
        kw['updated'] = time.strftime('%Y-%m-%d')
        cols = ','.join(kw); qs = ','.join('?'*len(kw))
        self.db.cursor().execute(f'INSERT OR REPLACE INTO {table}({cols}) VALUES({qs})', list(kw.values()))
        self.db.commit()
    def log(self, table, **kw):
        kw['updated'] = time.strftime('%Y-%m-%d')
        cols = ','.join(kw); qs = ','.join('?'*len(kw))
        self.db.cursor().execute(f'INSERT INTO {table}({cols}) VALUES({qs})', list(kw.values()))
        self.db.commit()
    def query(self, sql, args=()):
        return self.db.cursor().execute(sql, args).fetchall()
    def summary(self):
        return {t: self.query(f'SELECT COUNT(*) FROM {t}')[0][0]
                for t in ['theorems','predictions','assets','debts','frontier']}

class Panel:
    """立论(Prover)→证伪(Falsifier×N)→核验(Verifier=代码)→登记(Registrar) 回路"""
    def __init__(self, db, prover='deepseek', falsifiers=('longcat','kimi')):
        self.db = db; self.prover = prover; self.falsifiers = falsifiers
    def propose(self, topic, context):
        p = f"你是理论家。基于以下背景提出一条可证伪的候选定理(数学陈述, 含可检验预测, 80字内)。\n背景:\n{context}\n主题: {topic}"
        return chat(self.prover, p, max_tokens=300)
    def attack(self, candidate):
        verdicts = []
        for f in self.falsifiers:
            p = f"你是证伪者。攻击以下候选定理: 找反例/隐藏假设/循环论证。若无致命伤则说'通过'。(120字内)\n候选: {candidate}"
            v = chat(f, p, max_tokens=300)
            verdicts.append((f, v))
        return verdicts
    def aggregate(self, verdicts):
        """T26规则: 否决=最大池(任一证伪者发现致命伤→驳回), 共识=均值池(评语汇总)"""
        kills = [f for f, v in verdicts if any(w in v for w in ['反例','致命','循环','不成立','错误']) and '通过' not in v[:6]]
        return ('veto', kills) if kills else ('pass', [])


# ===================== APIKeyPool (ch44) =====================
class APIKeyPool:
    """API 密钥池：轮询 + 故障转移 + 速率感知"""
    def __init__(self, keys):
        if isinstance(keys, str):
            keys = [keys]
        self.keys = list(keys)
        self.failures = {k: 0 for k in self.keys}
        self.last_used = {k: 0.0 for k in self.keys}
        self.successes = {k: 0 for k in self.keys}

    def get(self):
        """获取最久未使用且健康的密钥"""
        healthy = [k for k in self.keys if self.failures[k] < 3]
        if not healthy:
            raise RuntimeError("All API keys exhausted")
        key = min(healthy, key=lambda k: self.last_used[k])
        self.last_used[key] = time.time()
        return key

    def report(self, key, ok):
        if ok:
            self.failures[key] = max(0, self.failures[key] - 1)
            self.successes[key] += 1
        else:
            self.failures[key] += 1

    def status(self):
        return {k: {"failures": self.failures[k], "successes": self.successes[k], 
                    "healthy": self.failures[k] < 3} for k in self.keys}

# 全局密钥池注册
KEY_POOLS = {}
def register_key_pool(name, keys):
    KEY_POOLS[name] = APIKeyPool(keys)

def get_key(name):
    return KEY_POOLS[name].get() if name in KEY_POOLS else None

def report_key(name, key, ok):
    if name in KEY_POOLS:
        KEY_POOLS[name].report(key, ok)
