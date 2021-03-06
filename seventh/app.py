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


class Conf:
    template = json.load(open(os.path.join(os.path.dirname(__file__), 'template.json')))
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
                self.values[k] = self.get_profit()
            elif self.values[k] - prev != 0:
                self.act(k, self.values[k] - prev, v_is_s=True)

    def get_profit(self):
        WORKING_DAYS_PER_MONTH = 30
        WORKING_HOURS_PER_DAY = 8
        return (WORKING_DAYS_PER_MONTH * WORKING_HOURS_PER_DAY *
                self.values['cosdi'] * self.values['couor'] - self.values['arebu']
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
    queue = asyncio.Queue()
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


async def meta_handler(request):
    return aiohttp.web.json_response(Conf.template)


handlers = [
    aiohttp.web.get('/', main_handler),
    aiohttp.web.get('/ws', websocket_handler),
    aiohttp.web.get('/meta', meta_handler),
]
logger = logging.getLogger(__name__)
REST_TIME = 1  # sec, to sleep between changes at client-side
