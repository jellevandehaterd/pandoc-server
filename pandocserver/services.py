import logging
import pathlib
import re
import shutil
import tarfile
import zipfile
from pathlib import Path
from typing import Union, IO, Any

import pypandoc

logger = logging.getLogger('asyncio')

__FORMATS = pypandoc.get_pandoc_formats()

PANDOC_SERVICE_INPUT_FORMATS = frozenset(__FORMATS[0])

PANDOC_SERVICE_OUTPUT_FORMATS = frozenset(['pdf'] + __FORMATS[1])

PANDOC_SERVICE_FORMATS = frozenset(PANDOC_SERVICE_INPUT_FORMATS | PANDOC_SERVICE_OUTPUT_FORMATS)


class ExtractArchiveError(Exception):
    pass


class NotAnArchiveError(ExtractArchiveError):
    pass


def extract_archive(filepath: Union[str, Path]) -> Path:
    archive = Path(filepath)

    suffixes = Path(archive.resolve()).suffixes
    ext = "".join(suffixes)

    compressions = {
        '.tar': 'tar',
        # gz
        '.gz': 'gz',
        '.tgz': 'gz',
        # xz
        '.xz': 'xz',
        '.txz': 'xz',
        # bz2
        '.bz2': 'bz2',
        '.tbz': 'bz2',
        '.tbz2': 'bz2',
        '.tb2': 'bz2',
        #zip
        '.zip': 'zip'
    }
    if suffixes[-1] not in compressions:
        raise NotAnArchiveError("Not an archive")

    stem = re.sub(f"{ext}$", "", archive.name)

    out_path = archive.parent / stem
    Path(out_path.resolve()).mkdir(mode=0o700, exist_ok=False)

    try:
        if archive.exists() and archive.is_file():
            if tarfile.is_tarfile(archive.resolve()):
                with tarfile.open(fileobj=archive.open(mode='rb'), mode='r:*') as tar_obj:
                    tar_obj.extractall(path=out_path.resolve())
            elif zipfile.is_zipfile(archive.resolve()):
                with zipfile.ZipFile(file=archive.resolve(), mode='r') as zip_obj:
                    zip_obj.extractall(path=out_path.resolve())
    except OSError as err:
        raise ExtractArchiveError(f"Unable to extract archive, reason: {err}")
    except tarfile.TarError as err:
        raise ExtractArchiveError(f"Unable to extract tar archive, reason: {err}")
    except (zipfile.BadZipFile, zipfile.LargeZipFile) as err:
        raise ExtractArchiveError(f"Unable to extract zip archive, reason: {err}")
    else:
        logger.debug(f"Extracted achive to {out_path.resolve()}")
        return out_path


class CreateArchiveError(Exception):
    pass


def create_archive(filepath: Union[str, Path], compression: str) -> Path:
    dir_to_archive = Path(filepath)

    if not dir_to_archive.is_dir():
        raise OSError(f"Not a directory: '{dir_to_archive.resolve()}'")

    try:
        if compression == '.zip':
            archive = Path(str(dir_to_archive.resolve()) + ".zip")
            with zipfile.ZipFile(file=archive.open(mode='wb+'), mode='w') as zip_obj:
                zip_obj.write(filename=dir_to_archive.resolve(), arcname=dir_to_archive.name)

        elif compression == '.tar' or compression in ('.gz', '.xz', '.bz2'):
            tar_mode = "w"
            archive = Path(str(dir_to_archive.resolve()) + ".tar")
            if compression in ('.gz', '.xz', '.bz2'):
                archive = Path(str(dir_to_archive.resolve()) + f".tar{compression}")
                tar_mode = f'w:{compression[1:]}'

            with tarfile.open(fileobj=archive.open(mode='wb+'), mode=tar_mode) as tar_obj:
                tar_obj.add(name=dir_to_archive.resolve(), arcname=dir_to_archive.name)
        else:
            raise CreateArchiveError(f"Invalid compression type: '{compression}'")

    except (OSError, ValueError, zipfile.LargeZipFile) as err:
        raise CreateArchiveError(f"Unable to create archive, reason: {err}")
    else:
        logger.debug(f"Created achive {archive.resolve()}")
        return archive
    finally:
        shutil.rmtree(dir_to_archive.resolve(), ignore_errors=True)
        logger.info(f"Cleaned up archived dir {dir_to_archive.resolve()}")


class PandocService(object):
    """
    Base class for converting provided HTML to a doc or docx
    """

    def __init__(self, **kwargs: dict):
        self.service = self.get_service()
        self._register_formats()
        self._source = None
        self._out_file = None
        self._from_format = None
        self._extra_args(**kwargs)

    def _extra_args(self, **kwargs):
        self.extra_args = []

        def parse_arg(arg, value):
            argument = None
            if type(value) == bool and value is True:
                argument = f"{arg}"
            elif type(value) != bool:
                argument = f"{arg}={value}"
            if argument is not None:
                self.add_argument(argument)

        if 'extra_args' in kwargs:
            for k, v in kwargs.pop('extra_args').items():
                parse_arg(k, v)

        for k, v in kwargs.items():
            parse_arg(k, v)

    @classmethod
    def _register_formats(cls) -> None:
        """Adds format properties."""
        for fmt in PANDOC_SERVICE_FORMATS:
            clean_fmt = fmt.replace('+', '_')
            setattr(cls, clean_fmt, property(
                (lambda x, fmt=fmt: cls._output(x, fmt)),  # fget
                (lambda x, y, fmt=fmt: cls._input(x, y, fmt))))  # fset

    def _input(self, source: IO[Any], from_format=None) -> None:
        if from_format not in PANDOC_SERVICE_INPUT_FORMATS:
            raise AttributeError(f"Not a valid input format: '{from_format}'")
        self._source = source
        self._form_format = from_format

    def _output(self, to_format, **kwargs) -> Union[str, pathlib.Path]:
        if to_format not in PANDOC_SERVICE_OUTPUT_FORMATS:
            raise AttributeError(f"Not a valid output format: '{to_format}'")

        to_format = 'latex' if to_format == 'pdf' else to_format

        kwargs = {
            'source_file': self._source,
            'to': to_format,
            'format': getattr(self, '_form_format', None),
            'extra_args': self.extra_args,
            'encoding': 'utf-8',
            'filters': kwargs.get('filters', None),
        }

        if self._out_file:
            kwargs["outputfile"] = str(self._out_file)
        return self.service.convert_file(**kwargs)

    @property
    def out_file(self) -> Union[str, pathlib.Path]:
        return self._out_file

    @out_file.setter
    def out_file(self, filepath: Union[str, pathlib.Path]) -> None:
        if filepath.parent.is_dir():
            self.add_argument('standalone')
            self._out_file = filepath
        else:
            raise OSError(f"Not a valid output dir: {filepath.parent.resolve()}")

    @staticmethod
    def get_service() -> pypandoc:
        return pypandoc

    def add_argument(self, arg) -> list:
        self.extra_args.append(f"--{arg.replace('_', '-')}")
        return self.extra_args
