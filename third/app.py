import aiohttp.web
import aiohttp.web_ws
import aiohttp_jinja2
import asyncio
import jinja2
import math
import logging
import sys

server_conf = dict(host='0.0.0.0', port=sys.argv[1] if len(sys.argv) > 1 else 8080)
app = aiohttp.web.Application()
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader('./templates'))
logging.basicConfig(
    format='[%(lineno)d] %(message)s',
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)

G = 9.780
DT = 0.1
C, RHO = 0.15, 1.29


class Conf:
    is_stopped = None
    a, v0, h0, s, m = [None] * 5
    _vx, _vy, _t, _x, _y, _cosa, _sina, _k = [None] * 8

    def set_data(self, a, v0, h0, s, m, **_):
        self.a = a * math.pi / 180
        self.v0, self.h0, self.s, self.m = v0, h0, s, m

    def prepare(self):
        self._t = 0
        self._x = 0
        self._y = self.h0
        self._cosa = math.cos(self.a)
        self._sina = math.sin(self.a)
        self._k = 0.5 * C * RHO * self.s / self.m
        self._vx = self.v0 * self._cosa
        self._vy = self.v0 * self._sina

    def __next__(self):
        if self._y < 0:
            raise StopIteration()
        self.t += DT
        v = math.sqrt(self._vx ** 2 + self._vy ** 2)
        self._vx -= self._k * self._vx * v * DT
        self._vy -= (G + self._k * self._vy * v) * DT
        self._x += vx * DT
        self._y += vy * DT
        return self._x, self._y

    def validate(self):
        if self.a < -90 or self.a > 90:
            raise Exception('invalid angle')
        if self.m < 0:
            raise Exception('invalid weight')
        if self.s < 0:
            raise Exception('invalid size')


async def updater(ws, c: Conf, wait_for: asyncio.Future, queue):
    if not await wait_for:
        return
    t = 0
    while True:
        await asyncio.sleep(DT)
        if c.is_stopped:
            logger.debug('stopped')
            await c.is_stopped
        x, y = next(c)
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
    queue = asyncio.Queue(maxsize=100)
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
                conf.set_data(**msg)
                conf.prepare()
                conf.validate()
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


if __name__ == '__main__':
    app.add_routes([
        aiohttp.web.get('/', main_handler),
        aiohttp.web.get('/ws', websocket_handler),
        aiohttp.web.static('/static', 'static'),
    ])
    aiohttp.web.run_app(app, **server_conf)
