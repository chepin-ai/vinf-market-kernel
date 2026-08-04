#!/usr/bin/env python3
"""v∞ Engine — 自证伪理论机器的第三方可复用门面(第55章)
一个类暴露全部引擎能力; 不绑定任何具体领域(换workdir即换域)。

    from engine import Engine
    e = Engine('/path/to/kernel')          # 含 theory_db.sqlite + journal39.jsonl + kg.json
    e.verify()                             # 链完整性
    e.doctor()                             # 自检/自修复
    e.reason()                             # 自推演/自验证/自涌现
    e.export_ttl('/tmp/kg.ttl')            # 语义网表示
    e.run('REFRESH-CN')                    # 命令注册表
    e.status()                             # 状态包(dict)

CLI:  python3 engine.py status|verify|doctor|reason|ttl|commands|run <CMD> [--workdir DIR]
"""
import json
import os
import sys

WORK = os.path.dirname(os.path.abspath(__file__))


class Engine:
    VERSION = '2.6.0'

    def __init__(self, workdir=None):
        self.wd = os.path.abspath(workdir or os.environ.get('VINF_WORK') or WORK)
        os.environ['VINF_WORK'] = self.wd
        if self.wd not in sys.path:
            sys.path.insert(0, self.wd)
        os.chdir(self.wd)

    # —— 验证面 ——
    def verify(self):
        import vinf_console as vc
        return vc.verify_chain()

    def status(self):
        import vinf_console as vc
        return vc.status(write=True)

    # —— 自修复面 ——
    def doctor(self):
        import vinf_doctor
        return vinf_doctor.Doctor().run()

    # —— 推演面 ——
    def reason(self):
        import vinf_reasoner
        p, n = vinf_reasoner.Reasoner(
            db_path=os.path.join(self.wd, 'theory_db.sqlite'),
            kg_path=os.path.join(self.wd, 'kg.json'),
            pool_path=os.path.join(self.wd, 'pool.json'),
            bundle_path=os.path.join(self.wd, 'state_bundle.json')).run()
        return json.load(open(p))

    def export_ttl(self, out=None):
        import vinf_ontology
        return vinf_ontology.OntologyExporter(
            db_path=os.path.join(self.wd, 'theory_db.sqlite'),
            kg_path=os.path.join(self.wd, 'kg.json')).run(out)

    # —— 命令面 ——
    def commands(self):
        import vinf_commands
        return sorted(vinf_commands.COMMANDS)

    def run(self, cmd, arg=None):
        import vinf_commands
        return vinf_commands.execute(cmd, arg)

    # —— 金融面 ——
    def finance(self):
        import vinf_console as vc
        import vinf_finance
        return vinf_finance.FinanceEngine(vc._db()).run_all()

    # —— 数据面 ——
    def refresh_cn(self, days=10, full=False):
        import vinf_refresh_cn
        return vinf_refresh_cn.refresh(days=days, full=full)

    def info(self):
        v = self.verify()
        return dict(engine='v∞ Engine', version=self.VERSION, workdir=self.wd,
                    chain=v, protocols=['Git-first', '代码才判决(A2/T9)', '人在回路',
                                        '密钥不出境', '涌现须蒸馏(R7)'])


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    wd = None
    if '--workdir' in sys.argv:
        wd = sys.argv[sys.argv.index('--workdir') + 1]
    e = Engine(wd)
    cmd = args[0] if args else 'info'
    if cmd == 'verify':
        out = e.verify()
    elif cmd == 'status':
        out = e.status()
    elif cmd == 'doctor':
        out = e.doctor()
    elif cmd == 'reason':
        out = e.reason()
    elif cmd == 'ttl':
        p, a = e.export_ttl()
        out = dict(file=p, audit=a)
    elif cmd == 'commands':
        out = e.commands()
    elif cmd == 'run':
        out = e.run(args[1] if len(args) > 1 else 'DOCTOR')
    elif cmd == 'finance':
        out = e.finance()
    else:
        out = e.info()
    print(json.dumps(out, ensure_ascii=False, indent=1, default=str))


if __name__ == '__main__':
    main()
