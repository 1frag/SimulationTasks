import aiohttp.web
import os


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
