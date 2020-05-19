import aiohttp.web
import aiohttp_jinja2
import logging
import os
from typing import List
import random

from common.utils import draw_gist_by_stats, save_and_clear


async def main_handler(request: aiohttp.web.Request):
    if request.method == 'GET':
        ret_val = {'photos': []}
        for ph_name in os.listdir(dir_saved):
            ret_val['photos'].append({
                'src': f'/ninth/saved/{ph_name}',
                'alt': f'{ph_name}',
            })
        ret_val['n_photos'] = len(ret_val['photos'])
        return aiohttp_jinja2.render_template('index.html', request, ret_val)
    else:
        def choose(p: List['float']):
            a = random.random()
            for k, pk in enumerate(p):
                a -= pk
                if a < 0:
                    return k
            return len(p) - 1

        try:
            data = await request.json()
            n = int(data['N'])
            p = list(data['p'])
            assert p[-1] == 'auto'
            p[:-1] = list(map(lambda x: round(float(x), 3), p[:-1]))
            p[-1] = round(1 - sum(map(float, p[:-1])), 3)
            statistics = {i: 0 for i in range(len(p))}
            if n > 1e7:
                raise ValueError('N too long')
            for _ in range(n):
                statistics[choose(p)] += 1
            draw_gist_by_stats(statistics, n, p)
            path = save_and_clear(dir_saved)

            return aiohttp.web.json_response({
                'status': 200,
                'src': path,
            })
        except Exception as e:
            return aiohttp.web.json_response({
                'status': 400,
                'reason': str(e),
            })


handlers = [
    aiohttp.web.route('*', '/', main_handler),
    aiohttp.web.static('/saved', 'ninth/saved'),
]
dir_saved = os.path.join(os.curdir, 'ninth', 'saved')
logger = logging.getLogger(__name__)
