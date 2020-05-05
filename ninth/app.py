import aiohttp.web
import aiohttp_jinja2
import logging
import os
from typing import List
import random
import matplotlib.pyplot as plt
import uuid

from common.utils import trust_key_required


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
            if len(os.listdir(dir_saved)) > 63:
                class Stub:
                    headers = {'Authorization': os.getenv('TRUST_KEY')}

                await removing(Stub())
            for _ in range(n):
                statistics[choose(p)] += 1
            rects = plt.bar(*zip(*statistics.items()))
            plt.title(f'N={n}, probs={p}')
            for rect in rects:
                # more: https://matplotlib.org/3.1.3/gallery/lines_bars_and_markers/barchart.html
                height = rect.get_height()
                plt.annotate('{}'.format(round(height / n, 3)),
                             xy=(rect.get_x() + rect.get_width() / 2, height),
                             xytext=(0, 3),  # 3 points vertical offset
                             textcoords="offset points",
                             ha='center', va='bottom')
            path = os.path.join(dir_saved, str(uuid.uuid4().hex)) + '.png'
            plt.savefig(path)
            plt.clf()
            return aiohttp.web.json_response({
                'status': 200,
                'src': path,
            })
        except Exception as e:
            return aiohttp.web.json_response({
                'status': 400,
                'reason': str(e),
            })


@trust_key_required
async def removing(request):
    ret_val = dict(removed=0)
    for name in os.listdir(dir_saved):
        if not name.startswith('protected_'):
            path = os.path.join(dir_saved, name)
            os.remove(path)
            ret_val['removed'] += 1
    if ret_val['removed']:
        logger.warning(f'{ret_val["removed"]} files have been deleted')
    return aiohttp.web.json_response(ret_val)


handlers = [
    aiohttp.web.route('*', '/', main_handler),
    aiohttp.web.static('/saved', 'ninth/saved'),
    aiohttp.web.post('/rm', removing),
]
dir_saved = os.path.join(os.curdir, 'ninth', 'saved')
logger = logging.getLogger(__name__)
