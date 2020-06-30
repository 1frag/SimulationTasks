import aiohttp.web
import aiohttp_jinja2
import math
import random
import collections
from scipy.stats import chi2


class Stream:
    def __init__(self, rate):
        self.rate = rate
        self.freq = collections.defaultdict(lambda: 0)

    def work(self, time):
        a, n = 0, 0
        while a < time:
            a -= math.log(random.random()) / self.rate
            n += 1
        self.freq[n] += 1
        return n


class MegaStream:
    def __init__(self, *streams):
        self.streams = streams
        self.freq = collections.defaultdict(lambda: 0)

    def work(self, time):
        n = [s.work(time) for s in self.streams]
        self.freq[sum(n)] += 1
        return sum(n)

    def get_prob(self, n, time):
        lmb = sum(s.rate for s in self.streams)
        return math.pow(lmb * time, n) / math.factorial(n) * math.exp(-lmb * time)

    def stats_result(self, time, n):
        data = [self.work(time) for _ in range(n)]

        a, e = 0, 0
        for p in data:
            a += p * self.freq[p] / n
            e += self.get_prob(p, time)
        a_er = math.fabs((a - e) / e)

        v, d = -a * a, -e * e
        for p in data:
            v += self.freq[p] * (p ** 2)
            d += self.get_prob(p, time) * (p ** 2)
        v_er = math.fabs((v - d) / d)

        chi2_e = 0
        for p in data:
            pr = self.get_prob(p, time)
            chi2_e += (self.freq[p] - n * pr) * (self.freq[p] - n * pr) / (n * pr)

        chi2_crit = chi2.ppf(1 - 0.05, len(data) - 1)
        chi2_passed = chi2_e <= chi2_crit

        return dict(
            average=dict(emp=a, teor=e, error=a_er),
            variance=dict(emp=v, teor=d, error=v_er),
            chi2=dict(emp=chi2_e, crit=chi2_crit, passed=chi2_passed),
        )


@aiohttp_jinja2.template('index.html')
async def main_handler(request: aiohttp.web.Request):
    if request.method == 'GET':
        return {'nothing': True}

    data = await request.post()
    n, t, l1, l2 = map(float, map(data.get, ('n', 't', 'l1', 'l2')))
    s1, s2 = map(Stream, (l1, l2))
    ms = MegaStream(s1, s2)
    return ms.stats_result(t, int(n))


handlers = [
    aiohttp.web.route('*', '/', main_handler),
]
