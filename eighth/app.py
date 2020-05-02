import aiohttp.web
import aiohttp_jinja2
import random
import json
from typing import List
import logging


async def main_handler(request: aiohttp.web.Request):
    def choose(p: List['float']):
        a = random.random()
        for k, pk in enumerate(p):
            a -= pk
            if a < 0:
                return k
        return len(p) - 1

    if request.method == 'GET':
        return aiohttp_jinja2.render_template('index.html', request, {})
    else:
        try:
            data = await request.json()
            ps = data['p']
            return aiohttp.web.json_response({
                'status': 200,
                'result': choose(ps),
            })
        except (KeyError, ValueError, json.JSONDecodeError) as e:
            return aiohttp.web.json_response({
                'status': 400,
                'reason': str(e),
            })


logger = logging.getLogger(__name__)
handlers = [
    aiohttp.web.route('*', '/', main_handler),
]
