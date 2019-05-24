import logging
import os

import pathlib
import shutil
import signal
from pathlib import Path
from tempfile import gettempdir

from typing import Any, Optional, Union
from .services import PandocService as service

logger = logging.getLogger('asyncio')

_service = None

DEFAULT_TEMP_DIR = os.environ.get('PANDOC_TEMP_DIR', gettempdir() + '/.pandoc')


def warm(conf) -> None:
    logger.info("Warming up the service")

    # should be executed only in child processes
    signal.signal(signal.SIGINT, signal.SIG_IGN)
    tmp_dir = Path(DEFAULT_TEMP_DIR)
    tmp_dir.mkdir(mode=0o700, exist_ok=True)
    logger.debug(f"Creating tempdir {tmp_dir.resolve()}")
    global _service
    if _service is None:
        _service = service(**conf.__dict__)


def clean() -> None:
    logger.info("Cleaning up the service")
    # should be executed only in child processes
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    tmp_dir = Path(DEFAULT_TEMP_DIR)
    shutil.rmtree(tmp_dir.resolve(), ignore_errors=True)
    logger.debug(f"Removed tempdir {tmp_dir.resolve()}")
    global _service
    _service = None


def convert(in_file: Union[str, pathlib.Path],
            out_file: Union[str, pathlib.Path],
            from_format: Optional[str] = None,
            to_format: Optional[str] = None,
            service: Optional[Any] = None) -> str:

    logger.info(f"Converting document from '{from_format}' to '{to_format}'")

    assert type(in_file) is str

    if service is None:
        service = _service

    if service is None:
        raise RuntimeError('Service should be loaded first')

    setattr(service, from_format, in_file)
    service._out_file = out_file
    return getattr(service, to_format)
