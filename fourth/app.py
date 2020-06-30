import aiohttp.web
import aiohttp.web_ws
import aiohttp_jinja2
import asyncio
import jinja2
import logging
import random
import sys
import time
import traceback


class Conf:
    cur_top = []
    clients = []

    def __init__(self):
        self.login = None
        self.enable = True
        self.money = DEFAULT_MONEY
        self.count = DEFAULT_COUNT
        self.is_started = asyncio.Future()
        Conf.clients.append(self)

    def set_login(self, login):
        if login in names:
            raise ValueError()
        self.login = login
        names.add(login)

    @classmethod
    async def top_changer(cls):
        """ Корутина watch dog для cur_top """
        global names
        while True:
            cls.clients = list(filter(lambda x: x.enable, cls.clients))
            names = {c.login for c in cls.clients if c.enable}
            cls.cur_top = [
                {'name': cl.login, 'money': cl.money}
                for cl in sorted(cls.clients, key=lambda x: x.money)
            ]
            await asyncio.sleep(3)

    async def send_balance(self, ws):
        await ws.send_json({
            'cmd': 'balance',
            'money': self.money,
            'count': self.count,
        })


async def updater(ws, c: Conf):
    if not await c.is_started:
        return
    while not ws.closed:
        async with currency_changed['cond']:
            await currency_changed['cond'].wait()
            await ws.send_json({
                'cmd': 'upd',
                'x': currency_changed['x'],
                'y': currency_changed['y'],
                'top': Conf.cur_top,
            })


async def reader(ws, queue, conf):
    if ws is None:
        raise Exception('ws must be not None')
    try:
        async for msg in ws:  # type: aiohttp.web_ws.WSMessage
            if msg.type == aiohttp.WSMsgType.ERROR:
                queue.put_nowait({'cmd': '_stop'})
            else:
                queue.put_nowait(msg.json())
    finally:
        conf.enable = False


@aiohttp_jinja2.template('index.html')
async def main_handler(request):
    return {'current': custom_data['current']}


async def websocket_handler(request: aiohttp.web.Request):
    queue = asyncio.Queue()
    ws = aiohttp.web.WebSocketResponse()
    await ws.prepare(request)
    conf = Conf()
    await conf.send_balance(ws)

    _reader = asyncio.ensure_future(reader(ws, queue, conf))
    _updater = asyncio.ensure_future(updater(ws, conf))

    while not ws.closed:
        msg = await queue.get()
        try:
            logger.debug(msg)
            if msg['cmd'] == 'hi':
                try:
                    conf.set_login(msg['login'])
                except ValueError:
                    await ws.send_json({
                        'cmd': 'error',
                        'e': 'Такой логин уже существует',
                    })
                    await ws.close()
                    return
                await ws.send_json({
                    'cmd': 'pd',
                    'data': DATA,
                })
                conf.is_started.set_result(True)
            elif msg['cmd'] == 'buy':
                # купить еще одну акцию
                if DATA[-1]['y'] <= conf.money:
                    conf.money -= DATA[-1]['y']
                    conf.count += 1
                    await conf.send_balance(ws)
                else:
                    await ws.send_json({
                        'cmd': 'not_enough_money',
                    })
            elif msg['cmd'] == 'sell':
                # продать одну акцию
                if conf.count > 0:
                    conf.count -= 1
                    conf.money += DATA[-1]['y']
                    await conf.send_balance(ws)
                else:
                    await ws.send_json({
                        'cmd': 'not_enough_count',
                    })
            elif msg['cmd'] == '_stop':
                raise Exception('_stop')
        except Exception as e:
            logger.error(''.join(traceback.format_exc(e)))
            await ws.send_json({'cmd': 'error'})
            await ws.close()
            break


async def update_currency():
    def get_next(c, t=None):
        return {
            'x': time.time() * 1000 + (t * 1000 if t else 0),
            'y': custom_data['get_y'](c, t),
        }

    global DATA
    DATA.append(INITIAL_VALUE)
    for i in range(-COUNT_ONCE - 1, 0):
        DATA.append(get_next(DATA[-1]['y'], i))
    while True:
        new_c = max({'y': 0}, get_next(DATA[-1]['y']), key=lambda d: d['y'])
        DATA = DATA[::-1][:COUNT_ONCE][::-1] + [new_c]
        async with currency_changed['cond']:
            currency_changed['x'], currency_changed['y'] = DATA[-1]['x'], DATA[-1]['y']
            currency_changed['cond'].notify_all()
        await asyncio.sleep(1)


def on_start():
    asyncio.ensure_future(update_currency())
    asyncio.ensure_future(Conf.top_changer())


def get_y(c, t):
    print('using 4th lab')
    return c * (1 + K * (random.random() - 0.5))


handlers = [
    aiohttp.web.get('/', main_handler),
    aiohttp.web.get('/ws', websocket_handler),
]
logger = logging.getLogger(__name__)
COUNT_ONCE = 20
K, DATA = 0.02, []
INITIAL_VALUE = {'y': 73.95}
currency_changed = {
    'cond': asyncio.Condition(),
}
DEFAULT_MONEY = 5000
DEFAULT_COUNT = 0
names = set()
custom_data = {'get_y': get_y,
               'current': 'fourth'}
