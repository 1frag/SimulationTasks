import logging
import aiohttp_jinja2
import os


def init(app_name: str):
    def render(name: str, *args, **kwargs):
        name = os.path.join(app_name, 'templates', name)
        return aiohttp_jinja2.render_template(name, *args, **kwargs)

    return logging.getLogger(app_name), render
