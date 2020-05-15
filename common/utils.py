import aiohttp.web
import os
import random
from typing import List


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


def choose(p: List['float']):
    a = random.random()
    for k, pk in enumerate(p):
        a -= pk
        if a < 0:
            return k
    return len(p) - 1
