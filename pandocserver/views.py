import asyncio
import logging
import mimetypes
from functools import partial
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict
from concurrent.futures import ProcessPoolExecutor

import aiohttp_jinja2
from aiohttp import web
from multidict import CIMultiDict

from .worker import convert, DEFAULT_TEMP_DIR
from .utils import Config, clean_up_tempfile

logger = logging.getLogger('asyncio')


class SiteHandler:
    def __init__(self, conf: Config, executor: ProcessPoolExecutor) -> None:
        self._conf = conf
        self._executor = executor
        self._loop = asyncio.get_event_loop()

    @aiohttp_jinja2.template('index.html')
    async def index(self, request: web.Request) -> Dict[str, str]:
        return {}

    async def convert(self, request: web.Request) -> web.StreamResponse:
        data = await request.post()

        input_filename = Path(data['file'].filename).stem
        ext = Path(data['file'].filename).suffix

        from_format = 'markdown'
        to_format = 'pdf'

        r = self._loop.run_in_executor
        executor = request.app['executor']
        try:
            with (await r(
                    None,
                    partial(NamedTemporaryFile, suffix=f'{ext}', dir=DEFAULT_TEMP_DIR)
            )) as fobj, \
                    (await r(
                        None,
                        partial(NamedTemporaryFile, mode='w', suffix=f'.{to_format}', dir=DEFAULT_TEMP_DIR, delete=False)
                    )) as fobj_out:

                fobj.write(data['file'].file.read())

                logger.info(f"Created input file: '{fobj.name}'")

                try:
                    to_format = 'latex' if to_format == 'pdf' else to_format
                    out = await r(executor, convert, fobj.name, fobj_out.name, from_format, to_format)
                    logger.info(f"Conversion successful, created file: '{fobj_out.name}'")
                except RuntimeError as e:
                    logger.error(f"{e}")
                    raise
                except TypeError as e:
                    logger.error(f"{e}")
                    raise

                content_type, _ = mimetypes.guess_type(fobj_out.name)
                disposition = f'filename="{input_filename}{Path(fobj_out.name).suffix}"'

                if 'text' not in content_type:
                    disposition = 'attachment; ' + disposition

                headers = {
                    'Access-Control-Expose-Headers': 'Content-Disposition',
                    'Content-Disposition': disposition
                }
                return web.FileResponse(path=fobj_out.name, headers=CIMultiDict(headers))
        finally:
            self._loop.call_later(30, clean_up_tempfile, fobj_out.name)
