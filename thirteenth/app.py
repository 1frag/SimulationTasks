import aiohttp.web
import aiohttp_jinja2
import logging
import matplotlib.pyplot as plt
import os
import math
import random

from contextvars import ContextVar
from collections import Counter
from scipy.stats import chi2

from common.utils import (
    draw_gist_by_stats, save_and_clear, calculate_stats,
    on_error,
)


def choices(n):
    return Counter([gen.get().value() for _ in range(n)])


class NegativeBinomialDistribution:
    def __init__(self, *, r, p):
        self.r, self.p = r, p

    def probably(self, m):
        r, p = self.r, self.p
        return math.comb(m + r - 1, m) * (p ** r) * ((1 - p) ** m)

    def value(self):
        r, p = self.r, self.p
        return sum(map(int, [math.log(random.random(), 1 - p)
                             for _ in range(r)]))


def theoretical_inp():
    p0 = gen.get().probably(0)
    prps, min_, sum_, i = [p0], p0, p0, 0

    while 1 - sum_ > min_ and round(sum_, 6) != 1:
        i += 1
        pi = gen.get().probably(i)
        min_ = min(min_, pi)
        sum_ += pi
        prps.append(pi)
    return prps, len(prps)


@on_error(aiohttp.web.HTTPBadRequest)
async def main_handler(request: aiohttp.web.Request):
    r = int(request.query.getone('r', 0))
    p = float(request.query.getone('p', 0))
    N = int(request.query.getone('N', 0))
    if min([r, p, N]) == 0:
        return aiohttp_jinja2.render_template(
            'index.html', request, {}
        )
    if N > (10 ** 6):
        raise aiohttp.web.HTTPBadRequest()

    gen.set(NegativeBinomialDistribution(r=r, p=p))
    stats = choices(N)  # генерируем случайные события
    ti = theoretical_inp()

    # теоретические математическое ожидание и дисперсия
    e1, v1 = calculate_stats(*ti)

    ni_s = [(x[1] / N) for x in sorted(stats.items(), key=lambda x: x[0])]
    # эмпирические математическое ожидание и дисперсия
    e2, v2 = calculate_stats(ni_s, max(stats.keys()))

    er_of_e = round(100.0 * (abs(e1 - e2) / e1), 4)  # погрешность математического ожидания
    er_of_v = round(100.0 * (abs(v1 - v2) / v1), 4)  # погрешность дисперсии

    chi2N = 0
    for i, ni in stats.items():
        pi = gen.get().probably(i)
        chi2N += (ni * ni) / (N * pi)
    chi2N -= N  # Хи-квадрат эксперементальное
    chi_table = round(chi2.ppf(1 - ALF, ti[1] - 1), 3)  # табличное значение Хи-квадрат

    plt.subplots(figsize=(5.7, 6))
    plt.subplots_adjust(top=0.9, bottom=0.2, left=0.2)
    draw_gist_by_stats(stats, f'{N=}, probs={p}', N, need_annotate=False)
    plt.ylabel('n\u1D62 - количество выпадений i', fontdict=dict(size=16))
    plt.xlabel(f'i - события\n'
               f'Average: {e2:.3f} (error = {er_of_e:.3f}%)\n'
               f'Variance: {v2:.3f} (error = {er_of_v:.3f}%)\n\n'
               f'Chi-squared: {chi2N:.3f} <= {chi_table:.3f}'
               f' is {chi2N <= chi_table}')
    path = os.path.basename(save_and_clear(dir_saved))
    raise aiohttp.web.HTTPFound(f'/result?path={path}')


async def result_handler(request: aiohttp.web.Request):
    current = request.query.getone('path')
    others = os.listdir(dir_saved)
    return aiohttp_jinja2.render_template(
        'result.html', request, dict(current=current, others=others)
    )


handlers = [
    aiohttp.web.get('/', main_handler),
    aiohttp.web.get('/result', result_handler),
    aiohttp.web.static('/saved', 'thirteenth/saved'),
]
logger = logging.getLogger(__name__)
dir_saved = os.path.join(os.curdir, 'thirteenth', 'saved')
ALF = 0.05
gen: ContextVar[NegativeBinomialDistribution] = ContextVar('gen')
