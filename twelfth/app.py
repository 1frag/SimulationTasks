import aiohttp.web
import random
import logging
import math
import aiohttp_jinja2


def generate_score(intensity):
    m, S = -1, 0
    while not (S < - intensity):
        a = random.random()
        S += math.log(a)
        m += 1
    return m


async def main_handler(request: aiohttp.web.Request):
    try:
        sc1 = generate_score(float(request.query.getone('i1')))
        sc2 = generate_score(float(request.query.getone('i2')))
        summary = {
            sc1 > sc2: f'> {sc2}. Team 1 won!',
            sc1 < sc2: f'< {sc2}. Team 2 won!',
            sc1 == sc2: f'== {sc2}. It is draw!',
        }[True]
        result = f'{sc1} : {sc2}; ({sc1} {summary})'
    except (TypeError, KeyError) as e:
        print(e, e.__class__)
        result = None
    return aiohttp_jinja2.render_template(
        'index.html', request, dict(result=result)
    )


handlers = [
    aiohttp.web.get('/', main_handler),
]
logger = logging.getLogger(__name__)
