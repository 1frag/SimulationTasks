import aiohttp.web
import aiohttp.web_ws
import aiohttp_jinja2
import asyncio
import jinja2
import math
import logging
import sys

class Conf:
    a, v0, h0, cosa, sina, is_stopped = [None] * 6

    def get_x(self, t):
        return self.v0 * self.cosa * t

    def get_y(self, t):
        return self.h0 + self.v0 * self.sina * t - G * t * t / 2


async def updater(ws, c: Conf, wait_for: asyncio.Future, queue):
    if not await wait_for:
        return
    t = 0
    while True:
        await asyncio.sleep(DT)
        if c.is_stopped:
            logger.debug('stopped')
            await c.is_stopped
        x, y = c.get_x(t), c.get_y(t)
        await ws.send_json({
            'cmd': 'update',
            'x': x,
            'y': y,
            'time': t,
        })
        if y <= 0:
            queue.put_nowait({'cmd': '_stop'})
            break
        t += DT


async def reader(ws, queue):
    if ws is None:
        raise Exception('ws must be not None')
    async for msg in ws:  # type: aiohttp.web_ws.WSMessage
        if msg.type == aiohttp.WSMsgType.ERROR:
            queue.put_nowait({'cmd': '_stop'})
        else:
            queue.put_nowait(msg.json())


async def resizer(ws, c: Conf):
    D = (c.v0 * c.sina) ** 2 + 2 * G * c.h0
    t_max = (c.v0 * c.sina + math.sqrt(D)) / G
    max_x = c.get_x(t_max)
    max_y = c.h0 + ((c.v0 * c.sina) ** 2) / (2 * G)
    await ws.send_json({
        'cmd': 'resize',
        'maxX': max(3, max_x),
        'maxY': max(3, max_y),
    })


@aiohttp_jinja2.template('index.html')
async def main_handler(request):
    return request.__dict__


async def websocket_handler(request: aiohttp.web.Request):
    queue = asyncio.Queue()
    ws = aiohttp.web.WebSocketResponse()
    await ws.prepare(request)
    conf = Conf()

    was_init = asyncio.Future()
    _reader = asyncio.ensure_future(reader(ws, queue))
    _updater = asyncio.ensure_future(updater(ws, conf, was_init, queue))

    while True:
        msg = await queue.get()
        try:
            logger.debug(msg)
            if msg['cmd'] == '_stop':
                _reader.cancel()
                _updater.cancel()
                break
            elif msg['cmd'] == 'init':
                conf.h0 = msg['h0']
                conf.v0 = msg['v0']
                conf.a = msg['a'] / 180 * math.pi
                if msg['a'] < -90 or msg['a'] > 90:
                    raise Exception('invalid angle')
                conf.cosa = math.cos(conf.a)
                conf.sina = math.sin(conf.a)
                await resizer(ws, conf)
                was_init.set_result(True)  # старт updater-у
            elif msg['cmd'] == 'stop':
                conf.is_stopped = asyncio.Future()
            elif msg['cmd'] == 'continue':
                conf.is_stopped.set_result(True)
        except Exception as e:
            logger.error(f'error: {e}')
            await ws.send_json({'cmd': 'error'})
            await ws.close()


handlers = [
    aiohttp.web.get('/', main_handler),
    aiohttp.web.get('/ws', websocket_handler),
]
logger = logging.getLogger(__name__)

G = 9.780
DT = 0.1
