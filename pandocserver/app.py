import asyncio
from pathlib import Path

import aiohttp_jinja2
import click

import logging

import jinja2

from pandocserver.middlewares import init_middlewares
from .routes import init_routes
from .utils import init_config, Config, init_workers, TrafaretYaml, CONFIG_TRAFARET
from .views import SiteHandler

from aiohttp import web

LOGGER_FORMAT = "%(asctime)-12s %(levelname)-8s %(message)s"
logging.basicConfig(format=LOGGER_FORMAT, datefmt='%Y-%m-%d %H:%M:%S')
logger = logging.getLogger('asyncio')

MAJOR_VERSION = 0
MINOR_VERSION = 9
PATCH_VERSION = '0.rc1'
__short_version__ = '{}.{}'.format(MAJOR_VERSION, MINOR_VERSION)
__version__ = '{}.{}'.format(__short_version__, PATCH_VERSION)

path = Path(__file__).parent


def init_jinja2(app: web.Application) -> None:
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(str(path / 'templates'))
    )


async def init_app(conf: Config) -> web.Application:
    app = web.Application()
    executor = await init_workers(app, conf.workers, conf.document)
    init_config(app, conf)
    init_jinja2(app)
    handler = SiteHandler(conf, executor)
    init_routes(app, handler)
    init_middlewares(app)
    return app

@click.group()
def main():
    pass


@main.command()
@click.argument("config", envvar='PANDOC_SERVER_CONFIG', type=TrafaretYaml(CONFIG_TRAFARET))
def validate(config):
    """Validate configuration file structure."""
    click.echo("OK: Configuration is valid.")


@main.command()
@click.argument("config", envvar='PANDOC_SERVER_CONFIG', type=TrafaretYaml(CONFIG_TRAFARET))
@click.option('-v', '--verbose', count=True)
def run(config, verbose):
    logging.basicConfig(level=logging.DEBUG)
    logger.setLevel(logging.INFO)
    logger.info("Version: %s", __version__)

    logger.info("Starting Server")
    verbosity = logging.ERROR - verbose * 10
    level = sorted((logging.DEBUG, verbosity, logging.ERROR))[1]
    logger.setLevel(level)
    logger.info(f"Loglevel is: {logging.getLevelName(level)}")

    loop = asyncio.get_event_loop()
    app = loop.run_until_complete(init_app(config))
    web.run_app(app, host=config.app.host, port=config.app.port)
