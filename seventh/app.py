import aiohttp.web
import aiohttp.web_ws
import aiohttp_jinja2
import asyncio
import jinja2
import logging
import os
import sys
import json
import traceback

server_conf = dict(host='0.0.0.0', port=sys.argv[1] if len(sys.argv) > 1 else 8080)
app = aiohttp.web.Application()
path = os.path.dirname(os.path.realpath(__file__))
aiohttp_jinja2.setup(app, loader=jinja2.FileSystemLoader(path + '/templates'))
logging.basicConfig(
    format='[%(lineno)d] %(message)s',
    level=logging.DEBUG,
)
logger = logging.getLogger(__name__)
REST_TIME = 1  # sec, to sleep between changes at client-side

"""                                 0  |  1  |  2  |  3  |  4  |  5  |  6  |  7  |  8  |  9  |
[visre] Посещаемость ресторана  0)  X  |  ↗  |     |     |  ↗  |     |     |     |     |     |
[difme] Разнообразие меню       1)  ↗  |  X  |     |     |     |     |     |     |     |     |
[quase] Качество обслуживания   2)  ↗  |     |  X  |     |     |     |     |     |     |     |
[stuff] Персонал                3)     |     |  ↗  |  X  |     |     |     |  ↗  |     |     |
[couor] Количество заказов      4)     |     |     |  ↗  |  X  |  ↗  |     |     |     |     |
[prore] Прибыль ресторана       5)     |     |     |     |     |  X  |     |  ↗  |     |     |
[arebu] Аренда помещения        6)     |     |     |     |     |  ↘  |  X  |     |     |     |
[salpe] Зарплата персонала      7)     |     |     |     |     |     |     |  X  |     |     |
[cosdi] Стоимость блюд          8)  ↘' |     |     |     |     |  ↗  |     |     |  X  |     |
[pripr] Цена на продукты        9)     |     |     |     |     |     |     |     |  ↗  |  X  |
"""


class Conf:
    template = json.load(open(path + '/template.json'))
    fields = {x['id']: x for x in template['fields']}

    def __init__(self):
        self.values = {x['id']: x['initial'] for x in self.template['fields']}
        self._queue = asyncio.Queue()

    def act(self, uuid, s, v_is_s=False):
        v = s if v_is_s else (self.fields[uuid].get('atom', 1) * (1 if s == '+' else -1))
        self.values[uuid] += v
        for r in filter(lambda x: x['from'] == uuid, self.template['depends']):
            def runner(rule):
                def cb(to, coef):
                    self._queue.put_nowait((to, v * coef))

                f = asyncio.ensure_future(asyncio.sleep(rule.get('delay', 1)))
                f.add_done_callback(lambda _: cb(rule['to'], rule['coef']))

            runner(r)

    def update(self):
        summary = {k: 0 for k in self.fields.keys()}
        try:
            while True:
                uuid, value = self._queue.get_nowait()
                summary[uuid] += value
        except asyncio.QueueEmpty:
            pass
        for k, v in summary.items():
            prev, self.values[k] = self.values[k], max(self.values[k] + v, 0)
            if k == 'prore':
                self.act(k, self.get_profit(), v_is_s=True)
            if self.values[k] - prev != 0:
                self.act(k, self.values[k] - prev, v_is_s=True)

    def get_profit(self):
        return (self.values['cosdi'] * self.values['couor'] - self.values['arebu']
                - self.values['arebu'] - self.values['salpe'] * self.values['stuff'])


async def updater(ws, c: Conf):
    while not ws.closed:
        await asyncio.sleep(REST_TIME)
        c.update()
        await ws.send_json({
            'cmd': 'update',
            'values': [{
                'id': k,
                'value': v,
                'int': c.fields[k]
            } for k, v in c.values.items()],
        })


async def reader(ws, queue, conf):
    async for msg in ws:  # type: aiohttp.web_ws.WSMessage
        if msg.type == aiohttp.WSMsgType.ERROR:
            queue.put_nowait({'cmd': '_stop'})
        else:
            queue.put_nowait(msg.json())


@aiohttp_jinja2.template('index.html')
async def main_handler(request):
    return request.__dict__


async def websocket_handler(request: aiohttp.web.Request):
    queue = asyncio.Queue(maxsize=100)
    ws = aiohttp.web.WebSocketResponse()
    await ws.prepare(request)
    conf = Conf()

    _reader = asyncio.ensure_future(reader(ws, queue, conf))
    _updater = asyncio.ensure_future(updater(ws, conf))

    while not ws.closed:
        msg = await queue.get()
        try:
            logger.debug(msg)
            if msg['cmd'] == '_stop':
                raise Exception('_stop')
            elif msg['cmd'] == 'act':
                conf.act(msg['id'], msg['s'])

        except Exception as e:
            logger.error(''.join(traceback.format_exc(e)))
            await ws.close()


if __name__ == '__main__':
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    app.add_routes([
        aiohttp.web.get('/', main_handler),
        aiohttp.web.get('/ws', websocket_handler),
        aiohttp.web.static('/static', os.path.join(cur_dir, 'static')),
    ])
    aiohttp.web.run_app(app, **server_conf)
