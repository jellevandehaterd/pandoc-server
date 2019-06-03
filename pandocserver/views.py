import asyncio
import logging
import mimetypes
import re
from functools import partial
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Dict
from concurrent.futures import ProcessPoolExecutor

import aiohttp_jinja2
from aiohttp import web
from multidict import CIMultiDict


from .services import PANDOC_SERVICE_FORMATS
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
        reader = await request.multipart()

        field = await reader.next()
        assert field.name == 'from'
        from_format = str(await field.read(), 'utf-8')

        field = await reader.next()
        assert field.name == 'to'
        to_format = str(await field.read(), 'utf-8')

        field = await reader.next()
        assert field.name == 'file'
        filename = field.filename

        ext = "".join(Path(filename).suffixes)
        input_filename = re.sub(f"{ext}$", "", filename)

        assert from_format in PANDOC_SERVICE_FORMATS
        assert to_format in PANDOC_SERVICE_FORMATS

        r = self._loop.run_in_executor
        executor = request.app['executor']
        fobj_out = None
        try:
            with (await r(
                    None,
                    partial(NamedTemporaryFile, mode='wb', suffix=f'{ext}', dir=DEFAULT_TEMP_DIR)
            )) as fobj:
                size = 0
                while True:
                    chunk = await field.read_chunk()  # 8192 bytes by default.
                    if not chunk:
                        break
                    size += len(chunk)
                    fobj.write(chunk)
                fobj.seek(0)

                logger.info(f"Created input file '{fobj.name}' sized '{size}'")

                try:
                    fobj_out = await r(executor, convert, input_filename, fobj.name, from_format, to_format)
                    logger.info(f"Conversion successful, created file: '{fobj_out.name}'")
                except (RuntimeError, TypeError) as e:
                    logger.error(f"{e}")
                    raise

                content_type, _ = mimetypes.guess_type(str(fobj_out.resolve()))
                disposition = f'filename="{fobj_out.name}"'

                if 'text' not in content_type:
                    disposition = 'attachment; ' + disposition

                headers = {
                    'Access-Control-Expose-Headers': 'Content-Disposition',
                    'Content-Disposition': disposition,
                    'Content-Transfer-Encoding': 'binary'
                }
        except Exception as err:
            return web.Response(text=str(err), status=500)
        else:
            return web.FileResponse(path=str(fobj_out.resolve()), headers=CIMultiDict(headers))
        finally:
            if fobj_out is not None:
                self._loop.call_later(30, clean_up_tempfile, str(fobj_out.resolve()))
