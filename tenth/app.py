import aiohttp.web
import logging
import aiohttp_jinja2
import os
from common.utils import choose


async def main_handler(request: aiohttp.web.Request):
    try:
        n = int(request.query.get('n') or 0)
        ps = list(map(float, request.query.getall('p', [])))
        if len(ps) != 0:
            ps.append(1 - sum(ps or [0]))
            pretty_print_probs = list(map(lambda x: round(x, 3), ps))
        else:
            pretty_print_probs = None
        result = choose(ps) if (n and ps) else None
        return aiohttp_jinja2.render_template(
            'index.html', request, dict(n=n, ps=ps, result=result,
                                        prps=pretty_print_probs)
        )
    except Exception as e:
        logger.warning(e)


handlers = [
    aiohttp.web.get('/', main_handler),
]
dir_saved = os.path.join(os.curdir, 'ninth', 'saved')
logger = logging.getLogger(__name__)
