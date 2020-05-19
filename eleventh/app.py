import aiohttp.web
import aiohttp_jinja2
import logging
import matplotlib.pyplot as plt
import os

from collections import Counter
from scipy.stats import chi2

from common.utils import choose, draw_gist_by_stats, save_and_clear
from tenth.app import main_handler as helper  # we use previous start-page

# chi2.ppf(0.999, 10)
ALF = 0.05


def calculate_stats(p, m):
    average = sum(map(lambda i: p[i] * i, range(m)))
    variance = sum(map(lambda i: p[i] * (i ** 2), range(m))) - (average ** 2)
    return round(average, 4), round(variance, 4)


def choices(p, n, m):
    ret_val = {i: 0 for i in range(m)}
    ret_val.update(Counter([choose(p) for _ in range(n)]))
    return ret_val


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


@on_error(aiohttp.web.HTTPBadRequest)
async def main_handler(request: aiohttp.web.Request):
    ctx = await helper(request, fair=False)  # type: dict
    N = int(request.query.getone('N', 0))  # количество повторений опыта
    m = ctx.get('n', None)  # количество исходов
    if N == 0 or m is None or ctx['prps'] is None:
        return aiohttp_jinja2.render_template(
            'index.html', request, ctx
        )
    if N > (10 ** 6):
        raise aiohttp.web.HTTPBadRequest()
    # добавив еще одно значение спрашиваемое у пользователя
    ctx['prps'] = ctx['prps'][:m]  # мы получаем лишний элемент в конце списка
    # требуется удалить его для корректности изображения

    stats = choices(ctx['prps'], N, m)  # генерируем случайные события

    # теоретические математическое ожидание и дисперсия
    e1, v1 = calculate_stats(ctx['prps'], m)

    ni_s = [(x[1] / N) for x in sorted(stats.items(), key=lambda x: x[0])]
    # эмпирические математическое ожидание и дисперсия
    e2, v2 = calculate_stats(ni_s, m)

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
    draw_gist_by_stats(stats, N, ctx["prps"])
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
