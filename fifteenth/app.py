import aiohttp.web
import logging
import math
import asyncio
import random
import aiohttp_jinja2


async def ws_handler(request: aiohttp.web.Request):
    ws = aiohttp.web.WebSocketResponse()
    await ws.prepare(request)
    i = 0
    stats = [1, 0, 0]
    while not ws.closed:
        tau = math.log(random.random()) / Q[i][i]
        if sum(stats) > 1:
            await asyncio.sleep(tau * 3)
        a = random.random()
        for new_i, prob in enumerate(
                (-Q[i][j] / Q[i][i]) if (i != j) else 0
                for j in range(3)
        ):
            a -= prob
            if a <= 0:
                i = new_i
                stats[new_i] += 1
                N = sum(stats)
                await ws.send_json({
                    'state': STATES[i],
                    'all_states': STATES,
                    'series': [{
                        'name': 'Эмпирические данные',
                        'data': [stats[j] / N for j in range(3)],
                    }, {
                        'name': 'Теоретические данные',
                        'data': [FINAL_PROBS[j] for j in range(3)],
                    }],
                    'for_table': [STATES, stats],
                })
                break


@aiohttp_jinja2.template('index.html')
async def main_handler(request: aiohttp.web.Request):
    return {}


handlers = [
    aiohttp.web.route('*', '/ws', ws_handler),
    aiohttp.web.route('*', '/', main_handler),
]
Q = (
    (-0.4, 0.3, 0.1),
    (0.4, -0.8, 0.4),
    (0.1, 0.4, -0.5),
)
STATES = (
    'ясно', 'облачно', 'пасмурно',
)
'''
 | 4y+z=4x       | x=24/63
<  3x+4z=8y  => <  y=19/63
 | x+y+z=1       | z=20/63
'''
FINAL_PROBS = (
    24 / 63, 19 / 63, 20 / 63
)
logger = logging.getLogger(__name__)
