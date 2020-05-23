import aiohttp.web
import aiohttp_jinja2
import logging
import matplotlib.pyplot as plt
import os
import random
import math
import time
from typing import List

from scipy.stats import chi2

from common.utils import draw_gist_by_stats, save_and_clear


def calc_chi2(e, v, n, stats: List[float]):
    stats.sort()
    count_of_pieces = int(math.sqrt(n) + 1)
    len_of_piece = (stats[-1] - stats[0]) / count_of_pieces
    pieces = [[i * len_of_piece, (i + 1) * len_of_piece, 0]
              for i in range(count_of_pieces)]
    for x_ in stats:
        pieces[int(x_ / len_of_piece)][2] += 1

    def calc_pzu(x):
        return (1 / (math.sqrt(2 * math.pi * v))) * (math.e ** (-(x - e) * (x - e) / 2 * v))

    def calc_pi(a, b):
        return (b - a) * calc_pzu((a + b) / 2)

    return sum((ni * ni) / (n * calc_pi(a, b)) for ni, a, b in pieces) - n


def choices(k, e, v, N):
    def choose():
        zu = None
        if k == 1:
            zu = (sum(random.random() for _ in range(n)) - (n * e)) / math.sqrt(v * n)
        if k == 2:
            zu = sum(random.random() for _ in range(n)) - 6
            zu += (zu ** 3 - 3 * zu) / 240.0
        if k == 3:
            a1, a2 = random.random(), random.random()
            zu = math.sqrt(-2 * math.log(a1)) * math.cos(2 * math.pi * a2)
        if k == 4:
            a1, a2 = random.random(), random.random()
            zu = math.sqrt(-2 * math.log(a1)) * math.sin(2 * math.pi * a2)
        return zu

    start_at = time.time()
    ret_val = [choose() for _ in range(N)]
    return ret_val, time.time() - start_at


def on_error(exc):
    def wrapper(func):
        async def inner(req):
            try:
                return await func(req)
            except aiohttp.web.HTTPException:
                raise
            except Exception as e:
                logger.warning(e)
                raise exc()

        return inner

    return wrapper


def calculate_stats(stats, n):
    ex = sum(stats) / n
    dx = (sum(i * i for i in stats) / n) - (ex * ex)
    return ex, dx


@on_error(aiohttp.web.HTTPBadRequest)
async def main_handler(request: aiohttp.web.Request):
    e = float(request.query.getone('e', 0))  # mean
    v = float(request.query.getone('v', 0))  # variance
    N = int(request.query.getone('N', 0))  # количество повторений опыта
    k = int(request.query.getone('k', 0))  # вариант генерации

    if min(e, v, N, k) == 0:
        return aiohttp_jinja2.render_template(
            'index.html', request, {}
        )

    if N > (10 ** 6):
        raise aiohttp.web.HTTPBadRequest()

    stats, spend = choices(k, e, v, N)  # генерируем случайные события

    # теоретические математическое ожидание и дисперсия
    e1, v1 = e, v

    # эмпирические математическое ожидание и дисперсия
    e2, v2 = calculate_stats(stats, N)

    er_of_e = round(100.0 * (abs(e1 - e2) / e1), 4)  # погрешность математического ожидания
    er_of_v = round(100.0 * (abs(v1 - v2) / v1), 4)  # погрешность дисперсии

    chi2N = 0
    for i, ni in stats.items():
        pi = ctx['prps'][i]
        chi2N += (ni * ni) / (N * pi)
    chi2N -= N  # Хи-квадрат эксперементальное
    chi_table = chi2.ppf(1 - ALF, m - 1)  # табличное значение Хи-квадрат

    plt.subplots(figsize=(5.7, 6))
    plt.subplots_adjust(top=0.9, bottom=0.2, left=0.2)
    draw_gist_by_stats(stats, f'{N=}, probs={ctx["prps"]}', N)
    plt.ylabel('n\u1D62 - количество выпадений i', fontdict=dict(size=16))
    plt.xlabel(f'i - события\n'
               f'Average: {e2:.3} (error = {er_of_e:.3}%)\n'
               f'Variance: {v2:.3} (error = {er_of_v:.3}%)\n\n'
               f'Chi-squared: {chi2N:.3} <= {chi_table:.3}'
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
    aiohttp.web.static('/saved', 'eleventh/saved'),
]
logger = logging.getLogger(__name__)
dir_saved = os.path.join(os.curdir, 'eleventh', 'saved')
ALF = 0.05
n = 12
