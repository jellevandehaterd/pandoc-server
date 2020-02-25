import logging
import mimetypes

import os

import pathlib
import re
import shutil
import signal
from pathlib import Path
from tempfile import gettempdir

from typing import Any, Optional, Union

from .services import PandocService as service, \
    create_archive, CreateArchiveError, extract_archive, ExtractArchiveError, NotAnArchiveError

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


def convert(filename:  str,
            in_file: Union[str, pathlib.Path],
            from_format: Optional[str] = None,
            to_format: Optional[str] = None,
            service: Optional[Any] = None) -> Union[str, pathlib.Path]:

    if service is None:
        service = _service

    if service is None:
        raise RuntimeError('Service should be loaded first')

    assert type(in_file) is str

    in_file = Path(in_file)
    out_file = None
    converted_files = 0
    try:
        archive = extract_archive(in_file)
        archive_ext = "".join(archive.suffixes)
        archive_stem = re.sub(f"{archive_ext}$", "", archive.name)

        out_dir = Path(str(archive.parent.resolve() / archive_stem / filename) + '_converted')
        out_dir.mkdir(mode=0o700)
        for filepath in sorted(archive.glob("*/*.*")):
            if filepath.is_dir():
                continue
            ext = "".join(filepath.suffixes)
            stem = re.sub(f"{ext}$", "", filepath.name)
            out_file = Path(str(out_dir.resolve()) + f"/{stem}.{to_format}")
            service.out_file = out_file
            setattr(service, from_format, str(filepath.resolve()))
            getattr(service, to_format)
            logger.info(f"Created output file: {service.out_file.resolve()}")
            converted_files += 1

        out_file = create_archive(out_dir, compression=in_file.suffixes[-1])
        shutil.rmtree(out_dir.resolve(), ignore_errors=True)
    except NotAnArchiveError:
        logger.debug("Not an archive format, treating it as a file")
        out_file = Path(str(in_file.parent.resolve()) + f"/{filename}.{to_format}")
        service.out_file = out_file
        setattr(service, from_format, str(in_file))
        getattr(service, to_format)
        converted_files += 1

        logger.info(f"Converted document from '{from_format}' to '{to_format}'")
    except (CreateArchiveError, ExtractArchiveError, AttributeError, RuntimeError, OSError) as err:
        raise
    else:
        logger.info(f"Converted {converted_files} document(s) from '{from_format}' to '{to_format}'")
    return out_file
