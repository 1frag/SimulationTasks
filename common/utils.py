import aiohttp.web
import matplotlib.pyplot as plt
import os
import random
import seaborn as sns
import uuid

from typing import List, Union, Dict

LIMIT_SAVED_FILES = 64


def trust_key_required(func):
    def inner(request):
        try:
            key = request.headers.get('Authorization')
            if key != os.getenv('TRUST_KEY', key):
                raise KeyError
        except KeyError:
            raise aiohttp.web.HTTPForbidden()
        return func(request)

    return inner


def choose(p: List['float']):
    a = random.random()
    for k, pk in enumerate(p):
        a -= pk
        if a < 0:
            return k
    return len(p) - 1


def draw_gist_by_stats(stats, title, n, need_annotate=True):
    # more: https://matplotlib.org/3.1.3/gallery/lines_bars_and_markers/barchart.html
    sort_stats = sorted(stats.items(), key=lambda x: x[0])
    width = min([sort_stats[i + 1][0] - sort_stats[i][0] for i in range(len(sort_stats)-1)])
    rects = plt.bar(*zip(*stats.items()), width=0.8 * width)
    plt.title(title)
    for rect in rects:
        height = rect.get_height()
        plt.annotate(str(round(height / n, 3)) if need_annotate else '',
                     xy=(rect.get_x() + rect.get_width() / 2, height),
                     xytext=(0, 3),  # 3 points vertical offset
                     textcoords="offset points",
                     ha='center', va='bottom')


def save_and_clear(dir_saved):
    path = os.path.join(dir_saved, str(uuid.uuid4().hex)) + '.png'
    plt.savefig(path)
    plt.clf()
    clear_directory(dir_saved)
    return path


def clear_directory(dir_saved):
    if len(os.listdir(dir_saved)) <= LIMIT_SAVED_FILES:
        return
    for name in os.listdir(dir_saved):
        if not name.startswith('p_'):  # protected
            path = os.path.join(dir_saved, name)
            os.remove(path)


def calculate_stats(p: Union[Dict, List], m: int):
    if isinstance(p, list):
        p = dict(enumerate(p))
    average = sum(map(lambda i: p.get(i, 0) * i, range(m)))
    variance = sum(map(lambda i: p.get(i, 0) * (i ** 2), range(m))) - (average ** 2)
    return round(average, 4), round(variance, 4)


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
