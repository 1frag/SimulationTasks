import aiohttp.web
import aiohttp_jinja2
import asyncio
import collections
import logging
import math
import random
import time
import uuid

FREQ_CLIENTS = 0.9
_FIELDS = ('l', 'mu', 'n')
SERVICES = {}


class ClientAgent:
    def __init__(self, service):
        self.service = service

    async def go(self):
        # client agent
        service_time = exp_rv(self.service.mu)
        logger.info(f'Время обработки клиента: {service_time}')
        await asyncio.sleep(service_time)
        assert self.service.busy_windows > 0
        self.service.busy_windows -= 1
        async with self.service.cond:
            self.service.cond.notify_all()


class Service:
    def __init__(self, lmb, mu, n):
        self.lmb, self.mu, self.n = lmb, mu, n
        self.busy_windows = 0
        self.stopped = False
        self.queue = 0
        self.cond = asyncio.Condition()
        self.stats = collections.defaultdict(lambda: 0)

    async def _new_client_event(self):
        # street agent
        while not self.stopped:
            next_event_after = exp_rv(self.lmb)
            logger.info(f'Через {next_event_after} новый клиент')
            await asyncio.sleep(next_event_after)
            self.queue += 1
            async with self.cond:
                self.cond.notify_all()

    async def go(self):
        asyncio.ensure_future(self._new_client_event())
        while not self.stopped:
            async with self.cond:
                time0, bw = time.time(), self.busy_windows
                await self.cond.wait()
                self.stats[bw] += time.time() - time0

            while self.queue and self.busy_windows < self.n:
                c = ClientAgent(self)
                self.queue -= 1
                self.busy_windows += 1
                asyncio.ensure_future(c.go())

    def practice(self):
        all_time = sum(self.stats.values())
        if all_time == 0:
            return []
        return [self.stats[k] / all_time for k in range(self.n + 1)]


def theoretical(lmb, mu, n):
    p = lmb / mu
    p0 = math.pow(
        sum(math.pow(p, k) / math.factorial(k) for k in range(n + 1))
        + (math.pow(p, n + 1) / math.factorial(n) / (n - p)), -1
    )
    return [p0] + [
        math.pow(p, k) / math.factorial(k) * p0
        for k in range(1, n + 1)
    ]


@aiohttp_jinja2.template('index.html')
async def main_handler(request: aiohttp.web.Request):
    if request.method == 'GET':
        return {}

    data = await request.post()
    if not all(map(data.__contains__, _FIELDS)):
        raise aiohttp.web.HTTPBadRequest()

    l, mu, n = map(int, map(data.get, _FIELDS))
    pid = str(uuid.uuid4().int)
    SERVICES[pid] = Service(l, mu, n)
    asyncio.ensure_future(SERVICES[pid].go())

    return aiohttp.web.json_response({
        'theoretical': theoretical(l, mu, n),
        'practice': pid,
    })


async def practice_handler(request: aiohttp.web.Request):
    s: Service = SERVICES.get(request.match_info['pid'])
    if s is None:
        raise aiohttp.web.HTTPBadRequest(body=f'{SERVICES=}')

    return aiohttp.web.json_response({
        'practice': s.practice(),
        'freq': f'{s.busy_windows} / {s.n}',
        'stats': s.stats,
    })


def exp_rv(lmd):
    return lmd * math.exp(-lmd * random.random())


handlers = [
    aiohttp.web.route('*', '/', main_handler),
    aiohttp.web.route('*', r'/practice/{pid:\d+}', practice_handler),
]
logger = logging.getLogger(__name__)
