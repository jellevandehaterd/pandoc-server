import asyncio
import click
import logging
from typing import Any, Dict, Union
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from aiohttp import web
import trafaret_config
import trafaret as t
from pathlib import Path
import os
from .worker import warm, clean

logger = logging.getLogger('asyncio')

PATH = Path(__file__).parent.parent
settings_file = os.environ.get('SETTINGS_FILE', 'api.yml')
DEFAULT_CONFIG_PATH = PATH / 'config' / settings_file

CONFIG_TRAFARET = t.Dict({
    t.Key('app'): t.Dict({
        t.Key('host'): t.String(),
        t.Key('port'): t.Int[0: 2 ** 16]
    }),
    t.Key('workers'): t.Dict({
        t.Key('max_workers'): t.Int[1:1024]
    }),
    t.Key('document'): t.Dict({
        t.Key('bibliography_path', optional=True): t.String,
        t.Key('citation_abbreviations_path', optional=True): t.String,
        t.Key('csl_path', optional=True): t.String,
        t.Key('template_path', optional=True): t.String,
        t.Key('extra_args', optional=True): t.Dict({}).allow_extra('*')
    }),
})


class TrafaretYaml(click.Path):
    """Configuration read from YAML file checked against trafaret rules."""
    name = "trafaret yaml file"

    def __init__(self, trafaret):
        self.trafaret = trafaret
        super().__init__(
            exists=True, file_okay=True, dir_okay=False, readable=True)

    def convert(self, value, param, ctx):
        cfg_file = super().convert(value, param, ctx)
        try:
            return config_from_dict(
                trafaret_config.read_and_validate(cfg_file, self.trafaret)
            )
        except trafaret_config.ConfigError as e:
            msg = "\n".join(str(err) for err in e.errors)
            self.fail("\n" + msg)


@dataclass(frozen=True)
class AppConfig:
    host: str
    port: int


@dataclass(frozen=True)
class WorkersConfig:
    max_workers: int


@dataclass(frozen=True)
class DocumentConfig:
    template_path: str = None
    csl_path: str = None
    bibliography_path: str = None
    citation_abbreviations_path: str = None
    extra_args: dict = field(default_factory=dict)


@dataclass(frozen=True)
class Config:
    app: AppConfig
    workers: WorkersConfig
    document: DocumentConfig


def config_from_dict(d: Dict[str, Any]) -> Config:
    app_config = AppConfig(  # type: ignore
        **d['app']
    )
    workers_config = WorkersConfig(  # type: ignore
        **d['workers']
    )
    document_config = DocumentConfig( # type: ignore
        **d['document']
    )
    return Config(app=app_config, workers=workers_config, document=document_config)  # type: ignore


def init_config(app: web.Application, config: Config) -> None:
    app['config'] = config


def clean_up_tempfile(filepath: Union[str, Path]):
    p = Path(filepath)

    if p.exists() and p.is_file():
        logger.debug(f"Cleaning up file '{p.name}'")
        p.unlink()


async def init_workers(app: web.Application, conf: WorkersConfig, doc: DocumentConfig) -> ProcessPoolExecutor:
    n = conf.max_workers
    executor = ProcessPoolExecutor(max_workers=n)

    loop = asyncio.get_event_loop()
    run = loop.run_in_executor
    fs = [run(executor, warm, doc) for i in range(0, n)]
    await asyncio.gather(*fs)

    async def close_executor(app: web.Application) -> None:
        fs = [run(executor, clean) for i in range(0, n)]
        await asyncio.shield(asyncio.gather(*fs))
        executor.shutdown(wait=True)

    app.on_cleanup.append(close_executor)
    app['executor'] = executor
    return executor
