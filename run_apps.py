import sys
import asyncio
import os
from num2words import num2words
import importlib.util
import aiohttp.web
import aiohttp_jinja2
import jinja2
import logging
import traceback
from typing import Dict, Tuple

BASE_PORT = 8800
logging.basicConfig(
    format='[%(lineno)d] %(message)s',
    level=logging.DEBUG,
)
CURRENT_APPS = dict()  # type: Dict[str, Tuple[aiohttp.web.AppRunner, aiohttp.web.TCPSite]]
loop = asyncio.get_event_loop()


def pull_from_target(target):
    names = {num2words(i, ordinal=True): i for i in range(1, 1000)}
    cur_path = os.getcwd()
    for dirname in os.listdir():
        path = os.path.join(cur_path, dirname)
        if os.path.isdir(path) and (dirname in names):
            num = names[dirname]
            if target in ['all', dirname, str(num)]:
                yield path, num


def all_directories_with_templates():
    for root_path, _ in pull_from_target('all'):
        yield os.path.join(root_path, 'templates')


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


async def start(dirname, num):
    app_name = os.path.join(dirname, 'app.py')
    static_path = os.path.join(dirname, 'static')
    templates_path = os.path.join(dirname, 'templates')
    spec = importlib.util.spec_from_file_location(app_name, app_name)
    app_file = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app_file)
    if hasattr(app_file, 'on_start'):
        app_file.on_start()  # noqa
    cur_app = aiohttp.web.Application()
    cur_app.add_routes(app_file.handlers + ([  # noqa
        aiohttp.web.static('/static', static_path),
    ] if os.path.isdir(static_path) else []) + [
        aiohttp.web.static('/common', 'common/static'),
    ])
    aiohttp_jinja2.setup(cur_app, loader=jinja2.FileSystemLoader(templates_path))
    runner = aiohttp.web.AppRunner(cur_app)
    await runner.setup()
    site = aiohttp.web.TCPSite(runner, port=BASE_PORT + num)
    await site.start()
    CURRENT_APPS[dirname] = (runner, site)


async def stop(dirname):
    runner, site = CURRENT_APPS[dirname]
    await site.stop()
    await runner.shutdown()
    del CURRENT_APPS[dirname]


@trust_key_required
async def start_handler(request: aiohttp.web.Request):
    ret_val = dict(success=0, skipped=0, failed=0)
    t = request.query['target']
    for dirname, num in pull_from_target(t):
        if dirname in CURRENT_APPS:
            logger.info(f'The {dirname} app has already been started.')
            ret_val['skipped'] += 1
            continue
        try:
            await start(dirname, num)
            ret_val['success'] += 1
            logger.info(f'The {dirname} app has just been started.')
        except Exception:
            ret_val['failed'] += 1
            logger.error(traceback.format_exc())
    ret_val.update({'status': 200 if ret_val['failed'] == 0 else 500})
    return aiohttp.web.json_response(ret_val)


@trust_key_required
async def stop_handler(request: aiohttp.web.Request):
    ret_val = dict(success=0, skipped=0, failed=0)
    t = request.query['target']
    for dirname, num in pull_from_target(t):
        if dirname not in CURRENT_APPS:
            logger.info(f'The {dirname} app has already been stopped.')
            ret_val['skipped'] += 1
            continue
        try:
            await stop(dirname)
            logger.info(f'The {dirname} app has just been stopped.')
            ret_val['success'] += 1
        except Exception:
            ret_val['failed'] += 1
            logger.error(traceback.format_exc())
    ret_val.update({'status': 200 if ret_val['failed'] == 0 else 500})
    return aiohttp.web.json_response(ret_val)


async def status_handler(request: aiohttp.web.Request):
    return aiohttp.web.json_response({
        'running': list(CURRENT_APPS.keys()),
    })


async def debug_handler(request):
    pass  # set breakpoint to debug current state


async def graceful_shutdown(application):
    failed = False
    logger.info('graceful_shutdown has been started')
    for dirname in list(CURRENT_APPS.keys()):
        try:
            await stop(dirname)
        except Exception as e:
            failed = True
            logger.error(traceback.format_exc())
    if failed:
        logger.info('graceful_shutdown has been completed with errors')
    else:
        logger.info('graceful_shutdown has been successfully completed')


if __name__ == '__main__':
    app = aiohttp.web.Application()
    aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('.'))
    app.add_routes([
        aiohttp.web.static('/common', 'common/static'),
        aiohttp.web.post('/start', start_handler),
        aiohttp.web.post('/stop', stop_handler),
        aiohttp.web.get('/status', status_handler),
        aiohttp.web.post('/debug', debug_handler),
    ])
    app.on_shutdown.append(graceful_shutdown)
    logger = logging.getLogger(__name__)
    port = sys.argv[1] if len(sys.argv) > 1 else BASE_PORT
    aiohttp.web.run_app(app, port=port)
