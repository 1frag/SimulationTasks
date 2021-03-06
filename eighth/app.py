import aiohttp.web
import aiohttp_jinja2
import random
import json
from typing import List
import logging
from common.utils import choose


async def main_handler(request: aiohttp.web.Request):
    if request.method == 'GET':
        return aiohttp_jinja2.render_template('index.html', request, {})
    else:
        try:
            data = await request.json()
            algo = data['algo']
            ps = data['p']
            if algo == 'one':
                return aiohttp.web.json_response({
                    'status': 200,
                    'result': int(random.random() > ps),
                })
            return aiohttp.web.json_response({
                'status': 200,
                'result': choose(ps),
            })
        except (KeyError, ValueError, json.JSONDecodeError, TypeError) as e:
            return aiohttp.web.json_response({
                'status': 400,
                'reason': str(e),
            })


logger = logging.getLogger(__name__)
handlers = [
    aiohttp.web.route('*', '/', main_handler),
]
