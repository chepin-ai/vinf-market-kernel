
# -*- coding: utf-8 -*-
"""v∞ ZKP 验证引擎 (ch44) —— 基于离散对数的简化 Schnorr 协议
T31: 自然=零知识Prover(只泄露现象不泄露机制), 实验=Verifier交互挑战
"""
import hashlib
import random

class ZKPProver:
    """Prover: 知道秘密 x，证明 g^x = y 而不泄露 x"""
    def __init__(self, g, p, x):
        self.g = g  # 生成元
        self.p = p  # 模数(大素数)
        self.x = x  # 秘密
        self.y = pow(g, x, p)  # 公开承诺

    def commit(self):
        """第一步: 发送承诺 t = g^r mod p"""
        self.r = random.randint(1, self.p - 2)
        self.t = pow(self.g, self.r, self.p)
        return self.t

    def respond(self, c):
        """第三步: 响应 s = r + c*x"""
        self.s = (self.r + c * self.x) % (self.p - 1)
        return self.s

    def get_public(self):
        return {'g': self.g, 'p': self.p, 'y': self.y}

class ZKPVerifier:
    """Verifier: 验证 g^s = t * y^c mod p，不学习 x"""
    def __init__(self, public):
        self.g = public['g']
        self.p = public['p']
        self.y = public['y']

    def challenge(self):
        """第二步: 随机挑战 c"""
        self.c = random.randint(1, self.p - 2)
        return self.c

    def verify(self, t, s):
        """验证: g^s ≡ t * y^c (mod p)"""
        lhs = pow(self.g, s, self.p)
        rhs = (t * pow(self.y, self.c, self.p)) % self.p
        return lhs == rhs

class KnowledgeProof:
    """知识证明: 将命题证明转化为 ZKP 交互"""
    def __init__(self, proposition):
        self.prop = proposition
        self.transcript = []

    def prove_knowledge(self, prover, verifier):
        """完整的三轮交互协议"""
        t = prover.commit()
        self.transcript.append(('commit', t))

        c = verifier.challenge()
        self.transcript.append(('challenge', c))

        s = prover.respond(c)
        self.transcript.append(('response', s))

        ok = verifier.verify(t, s)
        self.transcript.append(('verify', ok))

        return ok

    def get_transcript(self):
        """零知识:  transcript 不泄露秘密"""
        return self.transcript

def demo_zkp():
    """ZKP 演示: 证明知道离散对数而不泄露它"""
    p = 23  # 小素数用于演示(生产用2048位)
    g = 5
    x = 6   # 秘密

    prover = ZKPProver(g, p, x)
    verifier = ZKPVerifier(prover.get_public())

    proof = KnowledgeProof("I know log_g(y)")
    ok = proof.prove_knowledge(prover, verifier)

    return {
        'public': prover.get_public(),
        'transcript': proof.get_transcript(),
        'verified': ok,
        'zero_knowledge': 'transcript reveals nothing about x'
    }

if __name__ == '__main__':
    result = demo_zkp()
    print(json.dumps(result, indent=2))
