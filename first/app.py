import aiohttp.web
import aiohttp.web_ws
import aiohttp_jinja2
import asyncio
from typing import *
from copy import deepcopy
from enum import Enum, auto
import json
import logging


class State(Enum):
    WHITE = 1
    BLACK = 2
    GREEN = 3
    YELLOW = 4
    RED = 5
    BROWN = 6

    @staticmethod
    def default(o):
        if isinstance(o, State):
            return o.value
        else:
            raise TypeError()


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, State):
            return obj.value
        return json.JSONEncoder.default(self, obj)


def my_dumps(x):
    return json.dumps(x, cls=CustomEncoder)


class Task:
    class Type(Enum):
        CLOSE = auto()
        CHANGE_CONF = auto()
        DO_IT = auto()
        SEND = auto()
        UPGRADE = auto()
        NAME = auto()
        END = auto()

    def __init__(self, type_task: Type, data: Optional[Dict] = None):
        self.type = type_task
        self.data = data


class Item:
    color: State = State.WHITE
    tick: int = 0
    of: int = None

    def next(self):
        if self.of is not None:
            self.tick += 1
        if isinstance(self.of, int) and self.tick >= self.of:
            self.tick = 0
            self.color = NEXT_STATE[self.color]
            self.of = client_conf['settings'][self.color]

    def upgrade(self):
        cost = COSTS[self.color]
        if client_conf['score'] + cost < 0:
            return False
        client_conf['score'] += cost
        if self.color == State.WHITE:
            self.color = State.BLACK
        else:
            self.color = State.WHITE
        self.tick = 0
        self.of = client_conf['settings'][self.color]
        return True


async def send_history():
    HISTORY.sort(key=lambda x: x['score'], reverse=True)
    await ws.send_json({
        'cmd': 'history',
        'history': HISTORY,
    }, dumps=my_dumps)


async def updater():
    global cur_time

    def form(field):
        nonlocal i
        ret_val, i, j = [], 0, 0
        for r in field:
            for it in r:
                ret_val.append({
                    'i': i,
                    'j': j,
                    'color': it.color,
                    'tick': it.tick,
                    'of': it.of,
                })
                j += 1
            i += 1
            j = 0
        return ret_val

    while True:
        await asyncio.sleep(0.1)
        cur_time -= 0.1
        if cur_time <= 0:
            queue.put_nowait(Task(type_task=Task.Type.END))
            return
        for row in client_conf['field']:
            for i in row:  # type: Item
                i.next()
        queue.put_nowait(Task(type_task=Task.Type.SEND, data={
            'cmd': 'update',
            'field': form(client_conf['field']),
            'timer': int(cur_time),
        }))


async def reader():
    if ws is None:
        raise Exception('ws must be not None')
    async for msg in ws:  # type: aiohttp.web_ws.WSMessage
        if msg.type == aiohttp.WSMsgType.ERROR:
            break
        try:
            data = msg.json()
            cmd = data.pop('cmd')
            if cmd == 'change_conf':
                queue.put_nowait(Task(
                    type_task=Task.Type.CHANGE_CONF,
                    data=data,
                ))
            elif cmd == 'do_it':
                queue.put_nowait(Task(
                    type_task=Task.Type.DO_IT,
                    data=data,
                ))
            elif cmd == 'name':
                queue.put_nowait(Task(
                    type_task=Task.Type.NAME,
                    data=data['name'],
                ))
            elif msg.type == aiohttp.WSMsgType.ERROR:
                raise Exception('Websocket is closing')
            else:
                logger.warning(f'Unexpected command: {cmd=}')
                raise NotImplementedError()
        except Exception as e:
            queue.put_nowait(Task(
                type_task=Task.Type.CLOSE,
                data={'error': e},
            ))


def clean_up():
    global client_conf, cur_time, queue, ws
    if 'stop' in client_conf:
        client_conf['stop']()
    queue = asyncio.Queue()
    client_conf = {}
    cur_time = None
    ws = None


@aiohttp_jinja2.template('index.html')
async def main_handler(request):
    return request.__dict__


async def websocket_handler(request: aiohttp.web.Request):
    logger.debug('here1')
    global ws, client_conf, cur_time
    clean_up()
    cur_time = DEFAULT_TIME
    ws = aiohttp.web.WebSocketResponse()
    await ws.prepare(request)
    logger.debug('here2')
    settings = deepcopy(DEFAULT_SETTINGS)
    field = [
        [Item() for _ in range(4)]
        for _ in range(4)
    ]

    client_conf = {
        'score': DEFAULT_BUDGET,
        'field': field,
        'settings': settings,
    }

    _reader = asyncio.ensure_future(reader())
    _updater = asyncio.ensure_future(updater())

    def _stop():
        _reader.cancel()
        _updater.cancel()

    client_conf['stop'] = _stop

    async def update_settings():
        await ws.send_json({
            'cmd': 'settings',
            'settings': {i.value: j for i, j in settings.items()},
        }, dumps=my_dumps)

    await update_settings()
    while True:
        msg: Task = await queue.get()
        try:
            if msg.type == Task.Type.CLOSE:
                if not ws.closed:
                    logger.debug(msg.data)
                    await ws.send_json(msg.data)
                return
            elif msg.type == Task.Type.SEND:
                await ws.send_json(msg.data, dumps=my_dumps)
            elif msg.type == Task.Type.DO_IT:
                i, j = msg.data['i'], msg.data['j']
                if field[i][j].upgrade():
                    await ws.send_json({
                        'cmd': 'update_score',
                        'score': client_conf['score'],
                    }, dumps=my_dumps)
                else:
                    await ws.send_json({
                        'cmd': 'not_enough_money',
                    }, dumps=my_dumps)
            elif msg.type == Task.Type.CHANGE_CONF:
                from_state = int(msg.data['no'])
                new_value = int(msg.data['to'])
                client_conf['settings'][{
                    2: State.BLACK,
                    3: State.GREEN,
                    4: State.YELLOW,
                    5: State.RED,
                }[from_state]] = new_value
                await update_settings()
            elif msg.type == Task.Type.END:
                await ws.send_json({
                    'cmd': 'game_over',
                    'score': client_conf['score']
                }, dumps=my_dumps)
            elif msg.type == Task.Type.NAME:
                HISTORY.append({
                    'name': msg.data,
                    'score': client_conf['score'],
                })
                await send_history()
                await ws.close()
        except Exception as e:
            logger.error(f'error: {e}')


handlers = [
    aiohttp.web.get('/', main_handler),
    aiohttp.web.get('/ws', websocket_handler),
]
logger = logging.getLogger(__name__)
DEFAULT_TIME = 30  # время на игру
HISTORY = []  # результаты прошлых игр

cur_time = DEFAULT_TIME
client_conf = {}
queue = asyncio.Queue()
ws: Optional[aiohttp.web_ws.WebSocketResponse] = None

DEFAULT_BUDGET = 100
DEFAULT_SETTINGS = {
    State.WHITE: None,
    State.BLACK: 15,
    State.GREEN: 12,
    State.YELLOW: 9,
    State.RED: 9,
    State.BROWN: 'xxx',
}
NEXT_STATE = {
    State.WHITE: State.BLACK,
    State.BLACK: State.GREEN,
    State.GREEN: State.YELLOW,
    State.YELLOW: State.RED,
    State.RED: State.BROWN,
    State.BROWN: State.BROWN,
}
COSTS = {
    State.WHITE: -2,
    State.BLACK: -3,
    State.GREEN: 1,
    State.YELLOW: 3,
    State.RED: 5,
    State.BROWN: -5,
}
