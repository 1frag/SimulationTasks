import aiohttp.web
import logging
import aiohttp_jinja2
from common.utils import choose


async def main_handler(request: aiohttp.web.Request, *, fair=True):
    try:
        n = int(request.query.get('n') or 0)
        ps = list(map(float, request.query.getall('p', [])))
        if len(ps) != 0:
            ps.append(1 - sum(ps))
            pretty_print_probs = list(map(lambda x: round(x, 3), ps))
        else:
            pretty_print_probs = None
        result = choose(ps) if (n and ps) else None
        ctx = dict(n=n, ps=ps, result=result, prps=pretty_print_probs)
        if fair:
            return aiohttp_jinja2.render_template(
                'index.html', request, ctx
            )
        else:  # adapted for using in 11th lab
            return ctx
    except Exception as e:
        logger.warning(e)
        raise aiohttp.web.HTTPBadRequest()


handlers = [
    aiohttp.web.get('/', main_handler),
]
logger = logging.getLogger(__name__)
